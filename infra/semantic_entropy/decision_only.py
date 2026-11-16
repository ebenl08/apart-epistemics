"""Decision-only vs status-only SE (post-hoc robustness for Experiments 2 and 3; not pre-registered).

Run on the pod (2026-11-16 ~17:30 UTC+8) from the repo root with clm-env (m6env.sh):
  python3 infra/semantic_entropy/decision_only.py h1   # Experiment 2: partial rho / OLS for SE, decision-only, status-only
  python3 infra/semantic_entropy/decision_only.py h2   # Experiment 3: fixed-layer TBG probes (needs `h1` first: /root/contam_pts.pkl)
Definitions (paper section 3.6): decision-only SE = SE over samples with status ok (>= 2 needed, else NaN);
status-only SE = entropy of the status variable with all ok samples merged into one outcome.
"""
import sys
if __name__ == "__main__" and sys.argv[1:] == ["h1"]:
    import sys, glob, json, numpy as np, pandas as pd
    from collections import Counter
    sys.path.insert(0, "infra/semantic_entropy")
    from entropy import se_bits
    from analyze import load, partial_spearman, wall_of, boot_ci
    import statsmodels.formula.api as smf
    ST = {"invalid", "no_tool_call", "context_status", "error"}
    H = lambda ks: se_bits(list(Counter(ks).values())) if ks else 0.0
    out = {}
    for pre in ("m5-9b", "m5-9b-rl"):
        pts = load(pre)
        keys = pts.samples.apply(lambda ss: [s["key"] for s in ss])
        pts["se_dec"] = keys.apply(lambda k: H([x for x in k if x not in ST]) if sum(x not in ST for x in k) >= 2 else np.nan)
        pts["se_stat"] = keys.apply(lambda k: H(["ok" if x not in ST else x for x in k]))   # entropy of command/format status only
        pts["has_stat"] = keys.apply(lambda k: any(x in ST for x in k))
        out[pre] = pts
        tr = pts.groupby("trial").agg(family=("family","first"), level=("level","first"), reward=("reward","first"),
                                      se=("se_bits","mean"), se_dec=("se_dec","mean"), se_stat=("se_stat","mean"), fill=("fill","mean"), n=("t","size"))
        tr["wall"] = [wall_of(t) for t in tr.index]; tr = tr[~((tr.reward == 0) & ~tr.wall)].reset_index()
        tr["fl"] = tr.family + ":" + tr.level
        print(f"\n== {pre}: {len(pts)} points; points with any failed/format sample {pts.has_stat.mean():.1%}; "
              f"mean SE {pts.se_bits.mean():.3f}, decision-only {pts.se_dec.mean():.3f}, status-only {pts.se_stat.mean():.3f}")
        print(f"   trial-level corr(se, se_dec) = {np.corrcoef(tr.se, tr.se_dec)[0,1]:.2f}; corr(se, se_stat) = {np.corrcoef(tr.se, tr.se_stat)[0,1]:.2f}")
        for col in ("se", "se_dec", "se_stat"):
            f = lambda i, col=col: partial_spearman(tr[col].to_numpy()[i], tr.reward.to_numpy()[i], tr.fl.to_numpy()[i])
            rho = f(np.arange(len(tr))); ci = boot_ci(f, len(tr))
            m = smf.ols(f"reward ~ {col} + C(fl)", tr).fit()
            print(f"   H1 {col:8s}: partial rho {rho:+.3f} [{ci[0]:+.3f}, {ci[1]:+.3f}] | OLS coef {m.params[col]:+.2f} p={m.pvalues[col]:.4f}")
        m = smf.ols("reward ~ se_dec + se_stat + C(fl)", tr).fit()
        print(f"   joint OLS: se_dec {m.params['se_dec']:+.2f} (p={m.pvalues['se_dec']:.4f}), se_stat {m.params['se_stat']:+.2f} (p={m.pvalues['se_stat']:.4f})")
    pd.to_pickle(out, "/root/contam_pts.pkl")
if __name__ == "__main__" and sys.argv[1:] == ["h2"]:
    import glob, numpy as np, pandas as pd
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import GroupKFold
    from sklearn.metrics import roc_auc_score
    from scipy.stats import spearmanr
    pts_all = pd.read_pickle("/root/contam_pts.pkl")
    for pre, L in (("m5-9b", 20), ("m5-9b-rl", 28)):
        P = pts_all[pre].set_index(["trial", "t"])
        X, R = [], []
        for f in sorted(glob.glob(f"runs/m6-probe/{pre}__*.npz")):
            z = np.load(f); tr = f.split("/")[-1][:-4]
            for i, t in enumerate(z["t"]):
                X.append(z["tbg"][i, L].astype(np.float32)); R.append(P.loc[(tr, int(t))])
        X = np.stack(X); R = pd.DataFrame(R)
        g = R.index.get_level_values(0) if isinstance(R.index, pd.MultiIndex) else np.array([n[0] for n in R.index])
        base = np.c_[R.fill, [n[1] for n in R.index]]
        def cv(F, y, kind, mask=None):
            m = np.ones(len(y), bool) if mask is None else mask
            F, y, gg = F[m], y[m], np.asarray(g)[m]; pred = np.zeros(len(y))
            for tr, te in GroupKFold(5).split(F, y, gg):
                mdl = make_pipeline(StandardScaler(), LogisticRegression(C=0.05, max_iter=2000) if kind == "clf" else Ridge(alpha=1000.0)).fit(F[tr], y[tr])
                pred[te] = mdl.predict_proba(F[te])[:, 1] if kind == "clf" else mdl.predict(F[te])
            return roc_auc_score(y, pred) if kind == "clf" else spearmanr(y, pred).statistic
        ok = R.se_dec.notna().to_numpy()
        print(f"\n== {pre} layer {L} (TBG), {len(X)} points")
        for name, y, m in (("SE > 0 (original)", (R.se_bits > 0).to_numpy().astype(int), None),
                           ("decision-only SE > 0", (R.se_dec > 0).to_numpy().astype(int), ok),
                           ("status-only SE > 0 (failed cmd / format)", (R.se_stat > 0).to_numpy().astype(int), None)):
            print(f"   AUROC {name:42s}: activations {cv(X, y, 'clf', m):.3f} | fill+turn control {cv(base, y, 'clf', m):.3f} | positives {y[m if m is not None else slice(None)].mean():.1%}")
        y = R.se_dec.fillna(0).to_numpy()
        print(f"   Spearman decision-only SE (continuous): activations {cv(X, y, 'reg', ok):.3f} | fill+turn {cv(base, y, 'reg', ok):.3f}")

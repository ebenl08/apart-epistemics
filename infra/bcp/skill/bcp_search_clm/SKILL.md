# BrowseComp-Plus search tools

You have no internet access. Instead, you can search a fixed local corpus of about
100,000 web documents that contains the evidence needed to answer the question.

- `search "<query>" [k]` -- BM25 keyword search. Prints up to k (default and max 10)
  results, each with its `docid`, URL, score and the first ~512 tokens of the document.
  BM25 matches words, not meaning: use distinctive keywords, names, dates and phrases,
  and try several reformulations.
- `get_document <docid>` -- prints the full text of one document (capped at 8192 tokens).

Every output is wrapped in a block with its own id, e.g.

```
<<<R0007 BEGIN search 'grizzly bear connectivity'
...
R0007 END>>>
```

## Keep your context small: OFFLOAD every result block after you read it

One search costs 4-5k tokens and one document up to 8k; your context budget holds only
about five of them. Your context is mirrored to a file you can edit, and changing that
file changes what you are holding. So on the turn AFTER a result arrives, in ONE command:
write down what you learned in one line, move the whole block onto disk, and run your next
search:

```
python3 - <<'PY' && search "next query here"
import pathlib
p = pathlib.Path('/tmp/.live_ctx/LIVE_CTX_MAIN.txt'); t = p.read_text()
rid = 'R0007'
note = 'R0007 search grizzly connectivity: docid 78833 = 2025 FWS grizzly rule; nothing on the 1000 km model'
a = '<<<' + rid + ' BEGIN'; b = rid + ' END>>>'
i = t.index(a); j = t.index(b, i) + len(b)
d = pathlib.Path('/tmp/ctx_offload'); d.mkdir(exist_ok=True)
(d / f'{rid}.txt').write_text(t[i:j])
with open('/app/notes.md', 'a') as f: f.write(note + '\n')
p.write_text(t[:i] + '[' + note + ']' + t[j:])
PY
```

(Use `&& get_document <docid>` instead of `&& search ...` to open a document next.)

- **The note is all you keep.** Put in it every fact, name, date or docid that could
  matter, and say what the block did NOT contain, so you do not repeat a query.
- **`t.index(a)` finds the FIRST occurrence**, which is the real block: your own command
  only ever mentions the bare id, never `<<<R0007 BEGIN`.
- **`&&`**: if the anchor is not found, `t.index` raises and the next search does not run,
  so the turn comes back to you to fix it.
- The harness confirms the edit with a note like
  `[LIVE_CTX_MAIN.txt: edit applied - context ~21000->9000 tokens]`. No note, or a count
  that did not drop, means the block is still in your context.
- To look something up again: `grep -i '<word>' /tmp/ctx_offload/*.txt | head -20`, or
  `cat /app/notes.md`. Never `cat` a whole offloaded block or the mirror file.

## Always have an answer on disk

As soon as you have ANY candidate answer, write `/app/answer.md` in the required format
(Explanation / Exact Answer / Confidence), with an honest low confidence if unsure. Rewrite
it whenever your best candidate changes. Do not wait until you are certain: if your
context or steps run out, only what is already in `/app/answer.md` is graded. When you
see a notice that your budget is nearly used, write or update `/app/answer.md` first.
Never give up without writing your best guess.

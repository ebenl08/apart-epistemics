# BrowseComp-Plus search tools

You have no internet access. Instead, you can search a fixed local corpus of about
100,000 web documents that contains the evidence needed to answer the question.

- `search "<query>" [k]` -- BM25 keyword search. Prints up to k (default and max 10)
  results, each with its `docid`, URL, score and the first ~512 tokens of the document.
  BM25 matches words, not meaning: use distinctive keywords, names, dates and phrases,
  and try several reformulations.
- `get_document <docid>` -- prints the full text of one document (capped at 8192 tokens).

Search results and documents are long. Keep only what you need.

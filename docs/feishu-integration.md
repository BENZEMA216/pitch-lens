# Optional: publish reports to Feishu / Lark

PitchLens reports are just Markdown — share them however you like. If your team lives in **Feishu/Lark**, you can turn each report into a native doc and keep a master index, using the open‑source [`lark-cli`](https://github.com/larksuite/cli). Nothing here is required; the core tool writes plain `.md`.

> ⚠️ Reports contain candid scores, valuations, and terms. Keep docs **private by default** and share deliberately. Don't hardcode tokens in the repo.

## 1 · Install & log in
```bash
npm install -g @larksuite/cli      # or: npx @larksuite/cli
lark-cli auth login                # opens browser; logs in as your user
lark-cli doctor                    # confirms auth + connectivity
```

## 2 · One folder to hold everything
```bash
lark-cli drive +create-folder --name "Fundraising Reviews"
# → note the returned folder_token; export it so it's not hardcoded:
export FEISHU_FOLDER_TOKEN=<the_returned_token>
```

## 3 · Publish a report (Markdown → native Docx)
```bash
lark-cli docs +create --api-version v2 --doc-format markdown --content - \
    --parent-token "$FEISHU_FOLDER_TOKEN" < runs/2026-01-01-investor.md
# → returns data.document.url  (the shareable link)
```
The doc title comes from the Markdown's first H1. Tables/headings render natively. Setting link‑sharing scope may require you to click "Share" in the Feishu UI (API scope dependent).

## 4 · A master index that updates in place (no duplicates)
Create the index doc once, capture its `document_id`, then **overwrite** it each time instead of creating a new one:
```bash
# first time
lark-cli docs +create --api-version v2 --doc-format markdown --content - \
    --parent-token "$FEISHU_FOLDER_TOKEN" < runs/INDEX.md
# → capture data.document.document_id, then:
export FEISHU_INDEX_DOC=<the_returned_document_id>

# every update (same URL, full replace)
lark-cli docs +update --api-version v2 --command overwrite --doc-format markdown \
    --doc "$FEISHU_INDEX_DOC" --content - < runs/INDEX.md
```

A good `runs/INDEX.md` keeps: a top **dashboard** (per‑meeting trend table — temperature, score, next‑step, talk‑ratio; a question bank with model answers; a bad‑habits checklist), then one entry per meeting linking its transcript + report.

## 5 · Suggested per‑meeting flow
```bash
# after producing runs/<date>-<counterparty>.md and a relabeled transcript:
lark-cli docs +create … < runs/<date>-transcript.md     # → URL_T
lark-cli docs +create … < runs/<date>-<counterparty>.md # → URL_A
# add URL_T + URL_A under the meeting in runs/INDEX.md, then overwrite the index doc.
```

> zsh note: zsh doesn't word‑split unquoted variables — inline the command or use an array, don't `$CMD start`.

# 松居研究室 Webサイト (mtlab-web)

早稲田大学 人間科学部・大学院人間科学研究科 松居辰則研究室の Web サイトです．
[Hugo](https://gohugo.io/) で生成し，GitHub Pages で公開します．

公開URL: https://mtlab-waseda.github.io/mtlab-web/

## 必要なもの

- Hugo extended 0.168.0 以降 (`brew install hugo`)
- Python 3.12 (旧サイトからの移行スクリプトを再実行する場合のみ)

## ローカルでの確認

```sh
hugo server
# http://localhost:1313/mtlab-web/ を開く
```

## ディレクトリ構成

| パス | 内容 |
| --- | --- |
| `content/ja/` | 日本語ページ (Markdown) |
| `content/en/` | 英語ページ (Markdown) |
| `layouts/` | ページのテンプレート (ヘッダー・フッター等) |
| `assets/css/style.css` | スタイルシート |
| `static/img/` | 画像 (`static/img/design/` はサイトデザイン用) |
| `hugo.toml` | サイト設定・メニュー |
| `tools/scrape.py` | 旧サイト (PHP) からの移行スクリプト |

## ページの編集

`content/ja/*.md` を編集して `main` ブランチに push すると，GitHub Actions
(`.github/workflows/hugo.yml`) により自動でビルド・公開されます．

- 画像は `static/img/` に置き，本文中で `{{< figure src="/img/xxx.png" alt="説明" caption="キャプション" >}}` と書きます
  (`<img>` タグを直接書くと `/mtlab-web/` 配下で画像パスがずれるため，必ず `figure` を使ってください)．
- サイト内リンクは `[研究業績](/publications/)` のように書きます (`/mtlab-web/` は自動で付きます)．
  英語ページからのリンクも `/en/` を付けずに `/research/` と書けば英語版に解決されます．
- 構成員の表など，複雑な表は Markdown 内に HTML のまま書いています．
- メニューを変更する場合は `hugo.toml` の `menus.main` を編集します．

## URL 対応表 (旧 → 新)

| 旧URL | 新URL |
| --- | --- |
| `/index.php` | `/` |
| `/members.php` | `/members/` |
| `/research.php` | `/research/` |
| `/publications.php` | `/publications/` |
| `/welcome.php` | `/join/` |
| `/links.php` | `/links/` |
| `/ask.php` | `/contact/` |
| `/index-e.php` | `/en/` |
| `/research-e.php` | `/en/research/` |
| `/publications-e.php` | `/en/publications/` |
| `/ask-e.php` | `/en/contact/` |

旧URLには各ページの `aliases` によりリダイレクト用ページを生成しています
(独自ドメイン w-mtlab.info に切り替えた後に有効になります)．

## 移行スクリプトの再実行

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python tools/scrape.py
```

`content/` 以下と `static/img/` の画像を上書きするため，移行後に手で編集した内容は失われます
(リンク集の https 化などの修正も元に戻ります)．

## GitHub Pages の設定

1. リポジトリの Settings → Pages → Build and deployment の Source を「GitHub Actions」にする
2. `main` に push すると https://mtlab-waseda.github.io/mtlab-web/ に公開される

将来独自ドメイン (w-mtlab.info) に切り替える場合は，`hugo.toml` の `baseURL` を変更し，
Settings → Pages の Custom domain を設定して DNS を GitHub Pages に向けます．

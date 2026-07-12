# Deploying EuroCompass to Cloudflare Pages

This is a single file (`index.html`) that does everything: it loads live rates
straight from your GitHub repo every time someone opens the page. There is no
build step, no server, and no database. You just need to put this one file
somewhere Cloudflare can serve it from.

## Fastest method: drag-and-drop (no Git required)

1. Go to https://dash.cloudflare.com and log in (create a free account if you
   don't have one).
2. In the left sidebar, click **Workers & Pages**.
3. Click **Create** → the **Pages** tab → **Upload assets**.
4. Give the project a name, e.g. `eurocompass`.
5. Drag the `index.html` file (or the whole `eurocompass-site` folder) into
   the upload box.
6. Click **Deploy site**.

That's it. Cloudflare will give you a live URL like
`https://eurocompass.pages.dev` within about a minute.

## Better long-term method: connect your GitHub repo

This way, every time you push a change to your repo, the site rebuilds
automatically. Since this site has no build step, "rebuilding" just means
re-copying the file — instant.

1. In **Workers & Pages** → **Create** → **Pages**, choose
   **Connect to Git** instead of "Upload assets."
2. Select your `Pheonicx/eurocompass` repository.
3. When it asks for a **build command**, leave it blank.
4. When it asks for the **output directory**, point it at wherever you put
   `index.html` in your repo (for example, if you add this file at
   `site/index.html`, set the output directory to `site`).
5. Click **Save and Deploy**.

## A custom domain (optional)

Once deployed, go to your Pages project → **Custom domains** → **Set up a
domain**, and follow the prompts. You'll need a domain name you own (these
aren't free, but the Cloudflare Pages hosting itself still is).

## Why the data will always be current without you doing anything

The page fetches two things directly from your GitHub repo every time someone
opens it:

- `exports/latest.json` — today's rates for all banks
- `history/*.csv` — the historical data used for the 14-day trend chart

Your existing GitHub Actions workflow already updates both of these files
every hour. Because the site reads them live instead of having them baked in
at deploy time, **you never need to redeploy the site for new rates to show
up** — only if you want to change the design or logic itself.

## One thing to keep an eye on

If you ever make your GitHub repository private, this site will stop working,
because it reads `exports/latest.json` and `history/*.csv` directly from
GitHub's public raw file server, which only works for public repos.

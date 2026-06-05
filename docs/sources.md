# Source Catalog

Gospel Library IA keeps a controlled source catalog in PostgreSQL `sources`.

Each source stores:

- `sourceId`: stable source key.
- `name`: human readable name.
- `sourceType`: canonical search/filter type.
- `baseUrl`: discovery start URL.
- `language`: default language.
- `enabled`: whether scheduled/admin crawling may run.
- `crawlStrategy`: parser/discovery strategy.
- `rateLimit`: crawl budget hint.
- `maxPagesPerRun`: hard discovery limit for one run.
- `lastCrawledAt`: latest completed discovery timestamp.
- `robotsPolicyNotes`: operator notes for respectful crawling.

## Configured Sources

| sourceId | sourceType | Language | Base URL | Default limit |
| --- | --- | --- | --- | --- |
| `byu_speeches_es` | `byu_speeches_es` | `es` | `https://speeches.byu.edu/spa/talks/` | 12 |
| `byu_speeches_en` | `byu_speeches_en` | `en` | `https://speeches.byu.edu/talks/` | 12 |
| `discursos_sud` | `discursos_sud` | `es` | `https://discursosud.com/` | 10 |
| `general_conference` | `general_conference` | `es` | `https://www.churchofjesuschrist.org/study/general-conference` | 10 |
| `church_manuals` | `church_manuals` | `es` | `https://www.churchofjesuschrist.org/study/manual` | 10 |
| `joseph_smith_papers` | `joseph_smith_papers` | `en` | `https://www.josephsmithpapers.org/` | 8 |
| `byu_rsc` | `byu_rsc` | `en` | `https://rsc.byu.edu/` | 8 |
| `come_follow_me` | `church_manuals` | `es` | `https://www.churchofjesuschrist.org/study/manual/come-follow-me` | 8 |
| `teachings_presidents` | `church_manuals` | `en` | `https://www.churchofjesuschrist.org/study/manual/teachings-presidents` | 8 |
| `scriptures` | `scriptures` | `es` | `https://www.churchofjesuschrist.org/study/scriptures` | 8 |

## Admin Operations

Use the Admin dashboard section `Fuentes doctrinales` to:

- list configured sources;
- enable or pause a source;
- adjust `maxPagesPerRun`;
- run a crawl for one source;
- inspect document counts, errors, and last crawl time.

API endpoints:

```txt
GET   /api/admin/sources
PATCH /api/admin/sources/:sourceId
POST  /api/admin/sources/:sourceId/crawl
```

Admin endpoints require an admin session.

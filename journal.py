import json
import requests
import bibtexparser
import feedparser
import dateutil.parser
from bottle import Bottle, run, request
import sys


RSS_KEYS = [
    "prism_copyright",
    "prism_publicationname",
    "prism_number",
    "prism_volume",
    "prism_issn",
    "prism_coverdisplaydate",
    "link",
]


def get_issue(url, recursive=False):
    r = requests.get(url, params={"format": "bib"})
    bib_text = r.text
    bib_text = bib_text.replace('"\nparent_itemid', '",\nparent_itemid')
    bib_text = bib_text.replace('"\nauthor', '",\nauthor')
    bib_database = bibtexparser.loads(bib_text)
    articles = bib_database.entries
    if recursive:
        for a in articles:
            additional = get_issue(a["link"])
            if len(additional) == 1:
                for k in additional[0]:
                    if k not in a.keys():
                        a[k] = additional[0][k]
            a["authors"] = a["author"].split(" and ")
            a["lead_author"] = a["authors"][0]
            a["pages"] = [int(p) for p in a["pages"].split("-")]
            if "keyword" in a:
                a["keywords"] = a["keyword"].lower().split(", ")
            for i in ["year", "volume", "issue"]:
                if i in a:
                    a[i] = int(a[i])
    return articles


def get_issues(url):
    r = requests.get(url[0], params=url[1])
    d = feedparser.parse(r.text)
    issues = [{
        k.replace("prism_", ""): d[k] for k in d if k in RSS_KEYS
    } for d in d["entries"]]
    for i in issues:
        i["number"] = int(i["number"])
        i["volume"] = int(i["volume"])
        i["displaydate"] = str(dateutil.parser.parse(i["coverdisplaydate"]))
    return issues


def get_feed_url(publisher, journal):
    return (
        "http://api.ingentaconnect.com/content/{}/{}".format(publisher, journal),
        {"format": "rss"}
    )


app = Bottle()


@app.route('/<publisher>/<journal>/issues')
def journal_issues(publisher, journal):
    url = get_feed_url(publisher, journal)
    issues = get_issues(url)
    return {"issues": issues}


@app.route('/issue')
def journal_issues():
    url = request.query.link
    articles = get_issue(url, True)
    return {"articles": articles}


def main():
    port = 8080
    host = 'localhost'
    debug = True
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
        host = '0.0.0.0'
        debug = False
    run(app, host=host, port=port, debug=debug)

if __name__ == '__main__':
    main()

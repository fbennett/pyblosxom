"""
Summary
=======

This plugin implements news item listings for a subset
of Pyblosxom post categories, suitable for display
on a landing page. It is compatible with the pages
plugin.

There are several elements to the magic.

**Set date from filename** (cb_filestat)

For entry source files that begin with a yyyy-mm-dd string,
set the date of the post from the filename, overriding
the mtime value.

This works out nicely for keeping posts organized in a
filesystem view, and requires less overhead than extracting
the date from metadata recorded in the source file header.

**Ignore non-conformant filenames** (cb_truncatelist)

For categories specified in the "newslists" config list,
skip files that do not have a valid date prefix. This allows
README files and pre-release drafts to be set in these categories,
which is handy in a small-scale collaborative environment.

**Provide formatted link lists** (cb_prepare)

The categories specified in the "newslists" config list
are mapped as sorted, formatted link lists in the corresponding
(lowercased) variable names. The lists can be called in a
flavor template.

The composition of the link lists (number of items, and
whether the title is linked to an underlying post) is 
controlled by two values on the "newslists" config list objects.

Install
=======

To install, do the following:

1. Add ``newslists`` to the ``load_plugins`` list
   in your ``config.py`` file.

2. Specify a ``newslists`` config variable, like so:

   py["newslists"] = {
        "Alert":{
            "itemCount": 1,
            "useLink": False,
            "useDate": False
         },
         "News":{
            "itemCount": 6,
            "useLink": True,
            "useDate": False
         },
         "Events":{
            "itemCount": 6,
            "useLink": True,
            "useDate": True
         }
   }

3. Be sure that top-level category folders corresponding
   to the values set in the ``newslists`` variable
   are in place.

4. Add the (lowercased) newslist values to your page templates.
   For example:

   <div style="listing">$(news)</div>

The link templates are hard-wired. To change the HTML,
just edit the string templates in the plugin directly.

"""

__author__ = "Frank Bennett"
__email__ = "bennett at nagoya-u ac jp"
__version__ = "$Id$"
__url__ = "http://pyblosxom.github.com/"
__description__ = "Builds headline lists for three categories."
__category__ = "category"
__license__ = "MIT"
__registrytags__ = "1.4, 1.5, core"




from Pyblosxom import tools
from Pyblosxom.tools import pwrap
import os, re
import datetime,time

filerex = re.compile("^([0-9]{4})-([0-9]{2})-([0-9]{2})")

templates = {}
templates["date"] = {}
templates["nodate"] = {}
templates["date"]["link"] = "<div class='news-link'><i>@@date@@</i> - <a href='@@url@@'>@@title@@</a></div>"
templates["date"]["nolink"] = "<div style='background:yellow;text-align:center;'><b>Notice:</b> @@title@@ [@@date@@]</div>"
templates["nodate"]["link"] = "<div class='news-link'><a href='@@url@@'>@@title@@</a></div>"
templates["nodate"]["nolink"] = "<div style='background:yellow;text-align:center;'><b>Notice:</b> @@title@@</div>"

params = {}
paramsets["date"] = {}
paramsets["nodate"] = {}
paramsets["date"]["link"] = ["date","url","title"]
paramsets["date"]["nolink"] = ["date","title"]
paramsets["nodate"]["link"] = ["url","title"]
paramsets["nodate"]["nolink"] = ["title"]


def verify_installation(request):
    config = request.get_configuration()
    # Check for defined categories
    if not config['newslists']:
        print "Ouch 1"
        return False
    if not config['newslists'].keys():
        print "Ouch 2"
        return False
    for obj in config['newslists']:
        for key in ["count","link","usedate"]:
            if not obj.has_key(key):
                print "Ouch 3"
                return False
    print "Okay"
    return True


def cb_filestat(args):
    """Parse the entry filename looking for a date pattern. If the
    pattern matches and is a valid date, then override the mtime.
    
    """
    from Pyblosxom import tools
    filepath = args['filename']
    filelst = os.path.split(filepath)
    filename = filelst[-1]
    datadir = args['request'].getConfiguration()['datadir']
    logger = tools.getLogger()
    
    # If we find a date pattern in the filename, load it into the args
    # dict and return. If a pattern is not found, or if the values
    # in the yyyy-mm-dd prefix do not constitute a valid date,
    # return args unmolested.
    m = filerex.match(filename)
    if m:
        try:
            year = int(m.group(1))
            month = int(m.group(2))
            day = int(m.group(3))
            # Time values all set to zero in this implementation
            mtime = time.mktime((year,month,day,0,0,0,0,0,-1))
            stattuple = args['mtime']
            args['mtime'] = tuple(list(stattuple[:8]) + [mtime] + list(stattuple[9:]))
        except Exception as e:
            logger.error("%s: %s" % (type(e), e.args))
            return args
    return args

def cb_truncatelist(args):
    """For each entry under a named category, parse the entry filename
       looking for a date pattern. If the pattern does not match,
       delete the file from the list.
    """
    from Pyblosxom import tools
    logger = tools.getLogger()
    request = args['request']
    config = request.getConfiguration()
    category_names = config['newslists'].keys()
    category_configs = config['newslists']
    pagesdir = config['pagesdir']
    data = request.get_data()
    # The entry_list segment is a little funny inside
    # Pyblosxom. On most occasions it is double-nested when
    # this callback is invoked, so we don't return args
    # verbatim from this function.
    entry_list = args['entry_list']
    for i in range(len(entry_list) - 1, -1, -1):
        entry = entry_list[i]
        filepath = entry['file_path']
        # Check for path
        if filepath:
            # Split file path
            filelst = filepath.split(os.path.sep)
            # Always pass through index pages
            if filelst[-1] == "index":
                continue
            # Always pass through static pages
            if pagesdir and entry['filename'].startswith(pagesdir):
                continue
            # Check for dated config
            if categories:
                # Check for date pattern. This doesn't check
                # for date validity, only a looks-like-a-date
                # pattern.
                logger.debug("%s" % filelst[-1])
                if not filerex.match(filelst[-1]):
                    args['entry_list'].pop(i)
    return args['entry_list']


class GetNewsList:
    def __init__(self, config, categoryName, itemCount=6, useLink=True, useDate=True):
        self._config = config
        self._categoryName = categoryName
        self._count = itemCount
        if useLink:
            self._link = "link"
        else:
            self._link = "nolink"
        if useDate:
            self._date = "date"
        else:
            self._date = "nodate"
        self._news_list = None
        self.gen_news_list()

    def __str__(self):
        if self._news_list == None:
            self.gen_news_list()
        return self._news_list

    def gen_news_list(self):
        gottenStuff = []
        dirpath = os.path.join(self._config['datadir'], self._categoryName)
        files = os.listdir(dirpath)
        files.sort()
        files.reverse()
        count = 0
        stuff = []
        for filename in files:
            # Save some cycles on really common matches
            if filename == "README.txt" or filename.endswith("~"):
                continue
            m = filerex.match(filename)
            if m:
                # Snip off date
                year = int(m.group(1))
                month = int(m.group(2))
                day = int(m.group(3))
                # Format date

                # XXX Skip if date is invalid
                date = datetime.date(year, month, day).strftime("%e %b %Y (%a)").strip()

                # Open file
                ifh = open(os.path.join(dirpath, filename))
                # Get title
                title = ifh.readline()
                # Compose strings
                if title:
                    # Get template
                    template = templates[self._link][self._date]
                    # Get paramset
                    paramset = paramsets[self._link][self._date]
                    params = {}
                    for key in paramset:
                        if key == "title":
                            params['title'] = title.strip()
                        elif key == "url":
                            filestub = os.path.splitext(filename)[0]
                            filehtml = "%s.html" % filestub
                            base = self._config['base_url']
                            category = self._categoryName
                            params['title'] = os.path.join(base, category, filehtml)
                            while True:
                                line = ifh.readline()
                                if not line: break
                                if not line.startswith("#"): break
                                if line.startswith("#link ") and len(line) > 6:
                                    url = line[6:]
                                    break
                        elif key == "date":
                            params['date'] = date
                    for key in params:
                        entry = template.replace('@@%s@@' % key, params[key])
                    # Add to list
                    print "Adding"
                    stuff.append(entry)
                    count += 1
                    if count == self._count:
                        break
                ifh.close()
        # Join
        self._news_list = "\n".join(stuff)

def cb_prepare(args):
    request = args['request']
    config = request.get_configuration()
    base_url = config['base_url']
    if not base_url:
        base_url = ''
    data = request.get_data()
    logger = tools.get_logger()
    logger.debug(data['url'])
    if data['url'] == "%s/index.html" % base_url:
        # XXX Iterate over configured newslists
        for categoryName in config["newslists"].keys():
            key = categoryName.toLowerCase()
            cfg = config["newslists"][categoryName]
            data[key] = GetNewsList(config, categoryName, cfg['itemCount'], cfg['useLink'], cfg['useDate'])

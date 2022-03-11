import re


def bs_preprocess(html):
    """A preprocessor for HTML files that removes distracting whitespace so that traversing the DOM within BeautifulSoup
    is easier. From: https://groups.google.com/g/beautifulsoup/c/F3sdgObXbO4

    Args:
        html: the HTML to process

    Returns:
        The given HTML with annoying whitespace stripped
    """
    # https://groups.google.com/g/beautifulsoup/c/F3sdgObXbO4
    pat = re.compile('(^[\s]+)|([\s]+$)', re.MULTILINE)
    html = re.sub(pat, '', html)  # remove leading and trailing whitespaces
    html = re.sub(r'\n', ' ', html)  # convert newlines to spaces
    # this preserves newline delimiters
    html = re.sub(r'[\s]+<', '<', html)  # remove whitespaces before opening tags
    html = re.sub(r'>[\s]+', '>', html)  # remove whitespaces after closing tags
    return html

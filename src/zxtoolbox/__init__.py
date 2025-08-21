from textwrap import dedent

def cowsay(msg):
    """
    copy https://github.com/cs01/pycowsay/blob/master/pycowsay/main.py code
    :param msg:
    :return:
    """
    phrase = " ".join(msg)
    topbar = "-" * len(phrase)
    bottombar = "-" * len(phrase)
    output = dedent(
        """
      %s
    < %s >
      %s
       \   ^__^
        \  (oo)\_______
           (__)\       )\/\\
               ||----w |
               ||     ||
    """
        % (topbar, phrase, bottombar)
    )
    print(output)
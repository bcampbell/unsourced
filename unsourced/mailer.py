import smtplib
from email.mime.text import MIMEText
from cStringIO import StringIO
from email.generator import Generator


def send_email(addr_from, addr_to, subject, content):

    # would prefer to use utf-8, but that forces python to (stupidly) use
    # base64 content encoding.
    msg = MIMEText(content,_charset='iso-8859-1')

    msg['Subject'] = subject
    msg['From'] = addr_from
    msg['To'] = addr_to

    # hoopjumping to avoid mangling "From" at the beginning of lines.
    io = StringIO()
    g = Generator(io, mangle_from_=False)
    g.flatten(msg)

    s = smtplib.SMTP('localhost')
    s.sendmail(addr_from, [addr_to], io.getvalue())
    s.quit()


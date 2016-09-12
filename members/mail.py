from django.core.mail import EmailMultiAlternatives
from django.template import Template, Context
from django.template.loader import render_to_string
from django.shortcuts import render_to_response
from django.utils.html import strip_tags
from django.core.signing import Signer
from django.core.urlresolvers import reverse
import requests 
from .models import Invoice, TextBlock, MailType, Membership

mailgun_api_key = 'key-44e941ede1264ea215021bb0b3634eb4'
mailgun_api_url = 'https://api.mailgun.net/v3/mg.coombewoodltc.co.uk'

def do_mail(request, invoice, option):
    count = 0
    family = invoice.person.person_set.all()
    context={}
    TextBlock.add_email_context(context)
    invoice.add_context(context)
    signer = Signer()
    token = signer.sign(invoice.id)
    context['gc_bill_create'] = request.build_absolute_uri(reverse('invoice-public', args=(token,)))
    context['resign'] = request.build_absolute_uri(reverse('resigned'))
    if invoice.email_count > 0:
        context['reminder'] = True

    if family.count() > 0:
        context['junior_notes'] = TextBlock.objects.filter(name='junior_notes')[0].text
        context['family'] = family
    subject = "Coombe Wood LTC account"
    if option == 'view':
        return render_to_response("members/invoice_email.html", context)
        
    html_body = render_to_string("members/invoice_email.html", context)
    target = invoice.person.email if option == 'send' else "is@ktconsultants.co.uk"
    if target <> '':
        text_plain = strip_tags(html_body)
        msg = EmailMultiAlternatives(subject=subject,
                                        from_email="subs@coombewoodltc.co.uk",
                                        to=[target],
                                        body=text_plain)
        msg.attach_alternative(html_body, "text/html")
        msg.send()
        if option == 'send':
            invoice.email_count += 1
            count += 1
        invoice.save()
    return count




def send_template_mail(request, person, text, from_email, cc=None, bcc=None, subject="", mail_types=None, sent_list=[]):
    
    to = person.email
    recipient = person
    child =None
    if person.linked:
        if person.membership_id == Membership.JUNIOR or person.membership_id == Membership.CADET:
            recipient = person.linked
            child = person
    positive = False
    negative = False

    for mail_type in mail_types:
        if mail_type.person_set.filter(id=recipient.id):
            negative = True
        else:
            positive = True

    if negative and not positive:
        return 'unsubscribed'
    if recipient.email not in sent_list:
        sent_list.append(recipient.email)
        signer = Signer()
        token = signer.sign(recipient.id)
        context = Context({
            'first_name':recipient.first_name,
            'last_name': person.last_name})
        if child:
            context['child'] = child.first_name
        template = Template(text)
        html_body = template.render(context)
        unsub_url = request.build_absolute_uri(reverse('mailtype-subscribe-public', args=(token,)))
        html_body += '<p><a href="' + unsub_url + '">Unsubscribe</a></p>'
        if u'@' in to: 
            try:          
                send_htmlmail(from_email='Coombe Wood LTC <' + from_email + '>',
                                to=recipient.email,
                                subject=subject,
                                html_body=html_body)
                return 'sent'
            except Exception, e:       
                return 'bad email address'
        return False
    else:
        return 'duplicate'

        
def send_htmlmail(from_email, to, cc=None, bcc=None, subject="", html_body=""):
    '''
    Send HTML and plain test mail
    '''
    text_plain = strip_tags(html_body)
    msg = EmailMultiAlternatives(from_email=from_email,
                                to=[to],
                                cc=cc,
                                bcc=bcc,
                                subject=subject,
                                body=text_plain)
    msg.attach_alternative(html_body, "text/html")
    msg.send()

def send_simple_message():
    return requests.post(
        "https://api.mailgun.net/v3/sandbox5a84048e8637412db9d84372e91751d9.mailgun.org/messages",
        auth=("api", "key-44e941ede1264ea215021bb0b3634eb4"),
        data={"from": "Mailgun Sandbox <postmaster@sandbox5a84048e8637412db9d84372e91751d9.mailgun.org>",
              "to": "Heather <heathermca@hotmail.com>",
              "subject": "Hello Ian Stewart",
              "text": "Congratulations Ian Stewart, you just sent an email with Mailgun!  You are truly awesome!  You can see a record of this email in your logs: https://mailgun.com/cp/log .  You can send up to 300 emails/day from this sandbox server.  Next, you should add your own domain so you can send 10,000 emails/month for free."})

def mailgun_send():
    xx = requests.post(
        mailgun_api_url + '/messages',
        auth=("api", mailgun_api_key),
        data={"from": "info@coombewoodltc.co.uk",
              "to": "Ian Stewart <is@ktconsultants.co.uk>",
              "subject": "Hello Ian Stewart",
              "text": "Sent by the real thing"})
    return xx  
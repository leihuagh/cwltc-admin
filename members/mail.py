from django.core.mail import EmailMultiAlternatives
from django.template import Template, Context
from django.template.loader import render_to_string
from django.shortcuts import render_to_response
from django.utils.html import strip_tags
from django.core.signing import Signer
from django.core.urlresolvers import reverse
from django.http import HttpRequest
import requests 
from .models import Invoice, TextBlock, MailType, Membership, Settings

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
    context['resign'] = request.build_absolute_uri(reverse('public-resigned'))
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
    if target != '':
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

def send_multiple_mails(request, person_queryset, text, from_email,
                        cc=None, bcc=None, subject="", mail_types=None):
    count = 0
    count_unsub = 0
    count_bad = 0
    count_dups = 0
    sent_list = []
    year = Settings.current_year()
    for person in person_queryset:
        result = send_template_mail(request=request,
                                    person=person,
                                    text=text,
                                    from_email=from_email,
                                    cc=cc,
                                    bcc=bcc,
                                    subject=subject,
                                    mail_types=mail_types,
                                    sent_list=sent_list,
                                    year=year)
        if result == 'sent':
            count += 1
        elif result == 'unsubscribed':
            count_unsub +=1
        elif result == 'duplicate':
            count_dups += 1
        else:
            count_bad += 1
    return u'Sent: {}, Unsubscribed: {}, Duplicates: {}, No email address: {}'.format(
            count, count_unsub, count_dups, count_bad)

def send_template_mail(request, person, text,
                       from_email, cc=None, bcc=None, subject="",
                       mail_types=None, sent_list=None, year=0):
    if sent_list is None:
        sent_list = []
    if year == 0:
        year = Settings.current_year()
    recipient = person
    child = None
    if person.linked:
        # Get the current sub but deal with case in 
        # April when year is chnaged by sub is not yet there
        sub = person.active_sub(year)
        if not sub:
            sub = person.active_sub(year-1)
        if sub:
            if not sub.membership.is_adult:
                recipient = person.linked
                child = person
    to = recipient.email
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
        unpaid_invoices = recipient.invoices(state=Invoice.UNPAID)
        total_unpaid = 0
        invoice_urls = []
        if unpaid_invoices:
            for inv in unpaid_invoices:
                total_unpaid += inv.total
                token = signer.sign(inv.id)
                url= request.build_absolute_uri(reverse('invoice-public', args=(token,)))
                anchor ='<p><a href="' + url + '">Invoice ' + str(inv.id) + '</a><p>'
                invoice_urls.append(anchor)
        context = Context({
            'first_name':recipient.first_name,
            'last_name': recipient.last_name,
            'total_unpaid': total_unpaid,
            'invoice_urls': invoice_urls})
        if child:
            context['child'] = child.first_name
        template = Template(text)
        html_body = template.render(context)

        # Add an unsubscribe url    
        token = signer.sign(recipient.id)
        unsub_url = request.build_absolute_uri(reverse('mailtype-subscribe-public', args=(token,)))
        html_body += '<p><a href="' + unsub_url + '">Unsubscribe</a></p>'
        if u'@' in to: 
            try:          
                send_htmlmail(from_email='Coombe Wood LTC <' + from_email + '>',
                                to=recipient.email,
                                cc=cc,
                                bcc=bcc,
                                subject=subject,
                                html_body=html_body)
                return 'sent'
            except Exception:     
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
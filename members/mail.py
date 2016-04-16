from django.core.mail import EmailMultiAlternatives
from django.template import Context
from django.template.loader import render_to_string
from django.shortcuts import render_to_response
from django.utils.html import strip_tags
from django.core.signing import Signer
from django.core.urlresolvers import reverse

from .models import Invoice, TextBlock

def do_mail(invoice, option):
    count = 0
    family = invoice.person.person_set.all()
    context={}
    TextBlock.add_email_context(context)
    invoice.add_context(context)
    signer = Signer()
    token = signer.sign(invoice.id)
    context['gc_bill_create'] = reverse('invoice-public', args=(token,))
    context['resign'] = reverse('resigned', args=(token,))
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
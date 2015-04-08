from django.core.mail import EmailMultiAlternatives
from django.template import Context
from django.template.loader import render_to_string
from .models import Bill

def test_mail_template():
    pass
    #item1 = Bill(description = "Full subscription for 2014", amount = 250.00)
    #item2 = Bill(description = "Bar bill", amount = "123.45")
    #total = Bill(description = "Total now due", amount = "373.45")
    #item_list = [item1, item2]
    #template_data = {
    #    'name': "Ian Stewart",
    #    'item_list': item_list, 
    #    'total': total,
    #}

    #plaintext_context = Context(autoescape=False)  # HTML escaping not appropriate in plaintext
    #subject = "Test mail"
    #text_body = "Plain text"
    #html_body = render_to_string("members\subsmail.html", template_data)

    #msg = EmailMultiAlternatives(subject=subject, from_email="info@coombewoodltc.co.uk",
    #                             to=["is@ktconsultants.co.uk"], body=text_body)
    #msg.attach_alternative(html_body, "text/html")
    #msg.send()
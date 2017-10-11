import os
import gocardless_pro
from django.conf import settings

client = gocardless_pro.Client(
    access_token=getattr(settings, 'CARDLESS_ACCESS_TOKEN'),
    environment=getattr(settings, 'CARDLESS_ENVIRONMENT')
)

redirect_flow = client.redirect_flows.create(
    params={
        "description" : "Ale Casks", # This will be shown on the payment pages
        "session_token" : "dummy_session_token", # Not the access token
        "success_redirect_url" : "https://developer.gocardless.com/example-redirect-uri",
        "prefilled_customer": { # Optionally, prefill customer details on the payment page
            "given_name": "Tim",
            "family_name": "Rogers",
            "email": "tim@gocardless.com",
            "address_line1": "338-346 Goswell Road",
            "city": "London",
            "postal_code": "EC1V 7LQ"
        }
    }
)
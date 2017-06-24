from string import ascii_letters
from django.core.exceptions import ValidationError


class OneAlphaAndOneNumericValidator(object):
    '''
    Pasword must contain at least 1 character and 1 number and be at least 8 characters
    https://djangosnippets.org/snippets/2551/ 
    '''
    MESSAGE =  u"Your password must be at least 8 characters long and contain at least 1 letter and 1 number"
    
    def validate(self, password, user=None):
        characters = list(ascii_letters)
        numbers = [str(i) for i in range(10)]
        numCheck = False
        charCheck = False
    
        for char in password: 
            if not charCheck:
                if char in characters:
                    charCheck = True
            if not numCheck:
                if char in numbers:
                    numCheck = True
            if numCheck and charCheck:
                break
        
        if not numCheck or not charCheck or len(password) < 8:
            raise ValidationError(self.MESSAGE, code='invalid_password')
   
    def get_help_text(self):
        return self.MESSAGE

# from events.models import Event, EventType
#
# def validate_entrants(person, partner, event_type):
#     """
#     Check that gender is right for the competition.
#     Return None if OK else return an error message
#     """
#     err_male = 'Person must be male'
#     err_female = 'Person must be female'
#     err_partner_male = 'Your partner must be male'
#     err_partner_female = 'Your partner must be female'
#     err_no_partner = 'You must specify a partner'
#
#     if event_type == EventType.MENS_SINGLES:
#         if person.gender != 'M':
#             return err_male
#     elif event_type == EventType.LADIES_SINGLES:
#         if person.gender != 'F':
#             return err_female
#     elif event_type == EventType.MENS_DOUBLES:
#         if person.gender != 'M':
#             return err_male
#         if partner:
#             if partner.gender != 'M':
#                 return err_partner_male
#         else:
#             return err_no_partner
#     elif event_type == EventType.LADIES_DOUBLES:
#         if person.gender != 'F':
#             return err_female
#         if partner:
#             if partner.gender != 'F':
#                 return err_female
#         else:
#             return err_no_partner
#
#     elif event_type == EventType.MIXED_DOUBLES:
#         if partner:
#             if person.gender == 'F':
#                 if partner.gender != 'M':
#                     return err_partner_male
#             else:
#                 if partner.gender != 'F':
#                     return err_partner_female
#         else:
#             return err_no_partner
#     elif event_type == EventType.OPEN_SINGLES:
#         pass
#     elif event_type == EventType.OPEN_DOUBLES:
#         if not partner:
#             return err_no_partner
#     return None
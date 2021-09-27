from wtforms.validators import InputRequired, ValidationError

class RequiredIf(InputRequired):
    """
    Makes a field required if another field is set to a given value

    Sources:
    - https://wtforms.readthedocs.io/en/2.3.x/validators/
    - https://stackoverflow.com/questions/8463209/how-to-make-a-field-conditionally-optional-in-wtforms
    """
    field_flags = ('requiredif',)

    def __init__(self, other_field_name, other_field_value, *args, **kwargs):
        self.other_field_name = other_field_name
        self.other_field_value = other_field_value
        super(RequiredIf, self).__init__(*args, **kwargs)

    def __call__(self, form, field):
        other_field_name = form[self.other_field_name]
        if other_field_name is None:
            raise Exception(f"No field named {other_field_name} in form!")
        other_field_data = other_field_name.data
        print(f"Other field data: {other_field_data}")
        if other_field_data == self.other_field_value:
            super(RequiredIf, self).__call__(form, field)

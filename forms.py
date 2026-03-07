from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateField, TimeField, FloatField, PasswordField, HiddenField
from wtforms.validators import DataRequired, Email, Length, NumberRange, ValidationError
from datetime import date

class BookingForm(FlaskForm):
    customer_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    contact_number = StringField('Contact Number', validators=[DataRequired(), Length(min=7, max=20)])
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    address = TextAreaField('Event Address', validators=[DataRequired()])
    event_date = DateField('Event Date', validators=[DataRequired()])
    start_time = TimeField('Start Time', validators=[DataRequired()])
    end_time = TimeField('End Time', validators=[DataRequired()])
    equipment_id = SelectField('Equipment', coerce=int, validators=[DataRequired()])
    special_instructions = TextAreaField('Special Instructions')

    def validate_event_date(self, field):
        if field.data < date.today():
            raise ValidationError('Event date cannot be in the past.')

    def validate_end_time(self, field):
        if self.start_time.data and field.data <= self.start_time.data:
            raise ValidationError('End time must be after start time.')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

class EquipmentForm(FlaskForm):
    name = StringField('Equipment Name', validators=[DataRequired(), Length(max=100)])
    category = SelectField('Category', choices=[('sound', 'Sound System'), ('light', 'Lighting System'), ('videoke', 'Videoke / Karaoke')], validators=[DataRequired()])
    description = TextAreaField('Description')
    price_per_hour = FloatField('Price Per Hour (₱)', validators=[DataRequired(), NumberRange(min=0)])
    status = SelectField('Status', choices=[('available', 'Available'), ('unavailable', 'Unavailable')])

class ReportForm(FlaskForm):
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])

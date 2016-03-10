#!/usr/bin/env python
from flask import g, render_template, url_for, redirect, abort
from datetime import datetime, date, timedelta
from collections import OrderedDict
import json
import inspect
import os
import string
from application import app
import bills

@app.template_filter(name='ordinal')
def ordinal_filter(value):
    """ Take a number such as 62 and return 62nd. 63, 63rd etc.
        """
    digit = value % 10
    if 10 < value < 20:
        o = 'th'
    elif digit is 1:
        o = 'st'
    elif digit is 2:
        o = 'nd'
    elif digit is 3:
        o = 'rd'
    else:
        o = 'th'
    return '%d%s' % (value, o)
app.add_template_filter(ordinal_filter)

@app.template_filter(name='pluralize')
def pluralize(value):
    """ Add an 's' or an 'ies' to a word.
        We've got some special cases too.
        """
    plural = value
    if value[-1] == 'y':
        plural = '%sies' % value[:-1]
    else:
        plural += 's'
        
    return plural
app.add_template_filter(ordinal_filter)

@app.template_filter(name='datetime_raw')
def datetime_raw_filter(value):
    if not value:
        return None
    return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
app.add_template_filter(datetime_raw_filter)

@app.template_filter(name='date_raw')
def date_raw_filter(value):
    if not value:
        return None
    return datetime.strptime(value, '%Y-%m-%d')
app.add_template_filter(datetime_raw_filter)

@app.template_filter(name='datetimeformat')
def datetimeformat(value, format='%A %b. %d'):
    if not value:
        return None
    return value.strftime(format)

@app.template_filter(name='datetime')
def datetime_filter(value, format='datefull'):
    if format == 'full':
        format = "%A %b. %d, %I:%M %p"
    elif format == 'medium':
        format = "%A, %I:%M %p"
    elif format == 'datefull':
        format = "%b. %d"
    elif format == 'yeardatefull':
        format = "%b. %d %Y"
    elif format == 'weekday':
        format = "%a"
    try:
        return value.strftime(format).lstrip("0").replace(" 0", " ")
    except:
        return None
app.add_template_filter(datetime_filter)

@app.template_filter(name='bill_details')
def bill_details_filter(value, session):
    bill_id = string.replace(value['bill_id'].lower(), ' ', '_', )
    bill = json.load(bills.json_check('_input/%s/%s.json' % (session, bill_id)))
    return bill
app.add_template_filter(bill_details_filter)

@app.template_filter(name='chamber')
def chamber_filter(value):
    if value.lower() == 'lower':
        return 'House'
    return 'Senate'
app.add_template_filter(chamber_filter)

@app.template_filter(name='lowerfirst')
def lowerfirst_filter(value):
    # Decapitalize the first letter in the string.
    first = value[0].lower()
    return '%s%s' % (first, value[1:])
app.add_template_filter(lowerfirst_filter)

@app.template_filter(name='capfirst')
def capfirst_filter(value):
    """ Capitalize the first letter in the string.
        We can't use the capitalize filter because that one capitalizes the
        first letter and decapitalizes all the other ones (wut).
        """
    first = value[0].upper()
    return '%s%s' % (first, value[1:])
app.add_template_filter(capfirst_filter)

@app.template_filter(name='actiontosentence')
def actiontosentence_filter(value):
    """ Turn bill actions into something closer to a sentence.
        Examples of actions:
            In House - Assigned to Transportation & Energy
            Committee on Transportation & Energy Refer Amended to House Committee of the Whole
            Second Reading Passed with Amendments - Committee
            In Senate - Assigned to Transportation
            
            Signed by the President of the Senate
            Signed by the Speaker of the House
            Sent to the Governor
            Introduced In Senate - Assigned to Transportation
        """
    # There are certain words we're always going to lowercase
    value = value.replace('Assigned ', 'assigned ')
    value = value.replace('In ', 'in ')
    value = value.replace('Introduced ', 'introduced ')

    # Also, add a the to Senate / House references
    value = value.replace('in Senate', 'in the Senate')
    value = value.replace('in House', 'in the House')

    # This one doesn't work for some reason
    if 'Postpone Indefinitely' in value:
        value = value.rstrip(' Postpone Indefinitely')
        return 'postponed indefinitely by the %s' % value

    elif 'Refer Amended' in value or 'Refer Unamended' in value:
        value = 'the %s' % value
        value = value.replace('Refer Amended', 'committee referred an amended version')
        value = value.replace('Refer Unamended', 'committee referred an unamended version')
        value = value.replace('to House', 'to the House')
        value = value.replace('to Senate', 'to the Senate')
        return value

    elif 'Amendments' in value:
        """
            Third Reading Laid Over Daily - No Amendments
            Third Reading Passed - No Amendments
            Senate Third Reading Laid Over to 03/08/2016 - No Amendments
            Senate Third Reading Passed - No Amendments
            House Second Reading Passed - No Amendments
            House Third Reading Passed - No Amendments
            House Second Reading Passed with Amendments - Committee
            Senate Second Reading Referred to Appropriations - No Amendments
        """
        if '-' not in value:
            value = value.replace(' with Amendments', ' - Amendments')

        parts = value.split(' - ')
        # We separate the verb, which is Laid Over / Passed until the hyphen.
        if 'Passed' in parts[0]:
            verb = 'Passed'
        if 'Laid Over' in parts[0]:
            verb = 'Laid Over'
        elif 'Referred' in parts[0]:
            verb = 'Referred'
        elif 'Considered' in parts[0]:
            # This is likely some confusing stuff such as
            # House Considered Senate Amendments - Result was to Laid Over Daily
            # we're not touching that for now
            return value
        else:
            # Who knows what this is
            #print '***', value, '*part 0:', parts[0]
            return value
        verb_bits = parts[0].split(verb)
        #print value, verb_bits, parts[0]
        verb_phrase = '%s %s' % (verb, verb_bits[1])
        remainder = verb_bits[0].lower()
        remainder = remainder.replace('house', 'House\'s')
        remainder = remainder.replace('senate', 'Senate\'s')
        return '%s on the %s with %s' % (verb_phrase.lower(), remainder, parts[1].lower())

    elif 'introduced in ' in value:
        return value.replace('-', 'and')

    elif value[0:2] == 'in':
        parts = value.split(' - ')
        return '%s%s' % (parts[1], lowerfirst_filter(parts[0]))

    elif 'Signed by' or 'Sent to' in value:
        return lowerfirst_filter(value)
    return value
app.add_template_filter(actiontosentence_filter)

@app.template_filter(name='next_update')
def next_update(blank, value, delta=0):
    """ When is this / the next Tuesday, Wednesday, Thursday, Friday or Saturday?
        Returns a formatted date object, ala "Friday Feb. 20"
        Legit values for var value: "this" and "next"
        """
    today = date.today() + timedelta(delta)
    i = 1
    if value == 'this':
        i = 0 
    while i < 7:
        new_day = today + timedelta(i)
        wd = new_day.weekday()
        if wd in [0, 1,2,3,4,5]:
            return new_day.strftime('%A %b. %d')
        i += 1
    pass

@app.template_filter(name='timestamp')
def timestamp(blank):
    """ What's the current date and time?
        """
    today = datetime.today()
    return today.strftime("%A %b. %d, %-I:%M %p")

@app.template_filter(name='ifnone')
def ifnone(value, ifnone='~'):
    """ Pass a string other than "None" back if the value is None.
        Used in datestamp handling.
        """
    if value is None:
        return ifnone
    return value

@app.template_filter(name='legislator_lookup')
def legislator_lookup(value, field):
    """ Return a value from the dict of legislator data.
        """
    # import legislators
    try:
        return legislators.data[value.lower()][field.lower()]
    except:
        return None
app.add_template_filter(legislator_lookup)

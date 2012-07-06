from django.core.serializers.json import simplejson as json
from django.http import HttpResponse

from tastypie.bundle import Bundle
from tastypie.utils.mime import build_content_type
from tastypie.validation import FormValidation


class DefaultEnvelope(object):
    """
    Default envelope emulates what tastypie already sends out
    """
    def __init__(self, request_type, validation, response):
        self.request_type = request_type
        self.validation = validation
        self.response = response

    def process(self):
        pass

    def transform(self):
        return self.response


class MetaEnvelope(DefaultEnvelope):
    """
    Input:
        request_type: Tastypie's crappy way of handling single/multiple objects
        response: django HttpResponse to be sent

    Output:
        JSON content

    Follow the following envelope standard:

    If error is present data/pagination should be empty
    Status code should always be either 200 and status in meta will indicate
    what action to take

    {
        'meta': {
            'status': 200,
            'errors': {
                'form': {
                    'field1': [
                        'Error message 1',
                        'Error message 2'
                    ],
                    'field2': [
                        'Error message 3',
                        'Error message 4'
                    ]
                },
                'api': [
                    'Unknown exception occurred'
                ]
            },
            'pagination': {
                'limit': 20,
                'next': null,
                'offset': 0,
                'previous': null,
                'total_count': 1
            }
        },
        'data': {
            'username': 'adcde',
            'email': 'abcde@example.com'
        }
    }
    """

    def __init__(self, request_type, validation, response):
        super(MetaEnvelope, self).__init__(request_type, validation, response)
        self.status = 200
        self.errors = {}
        self.data = {}

        self.is_modified = False
        self.is_processed = False
        self.response_dict = {}

    def process(self):
        # Apply envelopes only to HttpResponse returning JSON
        content_type = self.response._headers.get('content-type', None)
        if content_type is not None and 'json' in content_type[1]:
            original_response_content = json.loads(self.response.content)

            # Create base meta structure
            self.response_dict = {
                'meta': {
                    'status': self.response.status_code,
                    'errors': {}
                },
                'data': {}
            }

            # Load data depending on whether its a list of object or a single object
            if self.request_type == 'list':
                self.response_dict['meta']['pagination'] = original_response_content['meta']
                self.data = original_response_content['objects']
            elif self.request_type == 'detail':
                self.data = original_response_content
            else:
                self.data = original_response_content

            # Load form errors if present
            if isinstance(self.validation, FormValidation):
                bundle = Bundle()
                bundle.data = self.data
                form_errors = self.validation.is_valid(bundle)
                if form_errors:
                    self.errors = {
                        'form': form_errors
                    }
                    self.response_dict['meta']['status'] = 400

            if self.response_dict['meta']['status'] >= 400:
                self.response_dict['meta']['errors']['api'] = [
                    'Invalid API request'
                ]

            self.response_dict['data'] = self.data
            self.is_modified = True

        self.is_processed = True

    def clear_data(self):
        self.response_dict['data'] = {}

    def transform(self):
        """
        After processing, the response structure can be edited before transform
        """
        if not self.is_processed:
            self.process()

        if self.errors:
            self.clear_data()
            if self.response_dict['meta']['status'] == 200:
                # If there are errors and status has not been updated then update status
                self.response_dict['meta']['status'] = 400

        if self.is_modified:
            return HttpResponse(
                content=json.dumps(self.response_dict),
                content_type=build_content_type('application/json')
            )
        else:
            return self.response

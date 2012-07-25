import copy
import logging

from django.core.serializers.json import simplejson as json
from django.http import HttpResponse

from tastypie.bundle import Bundle
from tastypie.utils.mime import build_content_type
from tastypie.validation import FormValidation


logger = logging.getLogger(__name__)


class DefaultEnvelope(object):
    """
    Default envelope emulates what tastypie already sends out
    """
    def __init__(self, validation, response):
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

    def __init__(self, validation=None, response=None, content=None):
        super(MetaEnvelope, self).__init__(validation, response)
        self.is_modified = False
        self.is_processed = False
        self.content = content

        self.response_data = {
            'meta': {
                'status': self.response and self.response.status_code or 200,
                'errors': {}
            },
            'data': {}
        }

    def process(self):
        # Apply envelopes only to HttpResponse returning JSON
        is_eligible = False

        if self.response is None and self.content is None:
            is_eligible = False
            logger.warning('Envelope initialized without response or raw content')
        elif self.content and isinstance(self.content, dict):
            if not(set(['meta', 'data']) < set(self.content.keys())):
                is_eligible = True
            else:
                logger.warning('Attempting to envelope response that is already enveloped')

            if is_eligible:
                self.update_data(self.content)
        elif self.response:
            content_type = self.response._headers.get('content-type', None)
            if content_type is not None and 'json' in content_type[1]:
                original_response_content = json.loads(self.response.content)

                if 'meta' not in original_response_content or 'data' not in original_response_content:
                    is_eligible = True
                else:
                    logger.warning('Attempting to envelope response that is already enveloped')

                if is_eligible:
                    # Load data depending on whether its a list of object or a single object
                    if 'meta' in original_response_content and 'objects' in original_response_content:
                        self.response_data['meta']['pagination'] = original_response_content['meta']
                        self.update_data(original_response_content['objects'])
                    else:
                        self.update_data(original_response_content)
        else:
            logger.warning('Response or data can not be enveloped')

        if is_eligible:
            # Load form errors if present
            if self.validation is not None and isinstance(self.validation, FormValidation):
                bundle = Bundle()
                bundle.data = self.response_data['data']
                form_errors = self.validation.is_valid(bundle)
                if form_errors:
                    self.add_errors('form', form_errors)
                    self.set_status(400)

            if self.contains_errors():
                self.set_status(400)

            self.is_modified = True
        else:
            logger.warning('Response or data can not be enveloped')

        self.is_processed = True

    def update_data(self, data):
        self.response_data['data'] = copy.deepcopy(data)

    def clear_data(self):
        self.response_data['data'] = {}

    def contains_errors(self):
        if self.get_status() >= 400 or self.get_errors():
            return True
        return False

    def get_errors(self):
        return self.response_data['meta']['errors']

    def add_errors(self, category, data):
        if category not in self.response_data['meta']['errors']:
            self.response_data['meta']['errors'][category] = {
                '__all__': []
            }

        if isinstance(data, dict):
            self.response_data['meta']['errors'][category] = copy.deepcopy(data)
        elif isinstance(data, (str, unicode)):
            if data not in self.response_data['meta']['errors'][category]['__all__']:
                self.response_data['meta']['errors'][category]['__all__'].append(data)

    def get_status(self):
        return self.response_data['meta']['status']

    def set_status(self, status_code):
        self.response_data['meta']['status'] = status_code
        if status_code == 400:
            self.add_errors('api', 'Invalid API request')
        elif status_code == 401:
            self.add_errors('api', 'Unauthorized API request')
        elif status_code == 403:
            self.add_errors('api', 'API request forbidden')
        elif status_code == 404:
            self.add_errors('api', 'Requested resource was not found')
        elif status_code == 405:
            self.add_errors('api', 'API method not allowed')
        elif status_code >= 500:
            self.add_errors('api', 'System error occurred')

    def build_response(self):
        return HttpResponse(
            content=json.dumps(self.response_data),
            content_type=build_content_type('application/json')
        )

    def transform(self):
        """
        After processing, the response structure can be edited before transform
        """
        if not self.is_processed:
            self.process()

        if self.is_modified:
            if self.contains_errors():
                if self.get_status() == 200:
                    # If there are errors and status has not been updated then update status
                    self.set_status(400)

            return self.build_response()
        else:
            if self.response is not None:
                return self.response
            else:
                if self.get_status() < 400:
                    self.set_status(500)
                return self.build_response()

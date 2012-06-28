from django.core.serializers.json import simplejson as json


class DefaultEnvelope(object):
    """
    Default envelope emulates what tastypie already sends out
    """
    def __init__(self, request_type, response):
        self.request_type = request_type
        self.response = response

    def transform(self):
        return self.response.content


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

    def __init__(self, request_type, response):
        super(MetaEnvelope, self).__init__(request_type, response)
        self.status = 200
        self.errors = {}
        self.data = {}

    def transform(self):
        # Apply envelopes only to HttpResponse returning JSON
        content_type = self.response._headers.get('content-type', None)
        if content_type is not None and 'json' in content_type[1]:
            original_response_content = json.loads(self.response.content)

            response_content = {
                'meta': {
                    'status': self.response.status_code,
                    'errors': {}
                },
                'data': {}
            }
            if self.request_type == 'list':
                response_content['meta']['pagination'] = original_response_content['meta']
                self.data = original_response_content['objects']
            elif self.request_type == 'detail':
                self.data = original_response_content
            else:
                self.errors = {
                    'api': [
                        'Invalid request type'
                    ]
                }
                response_content['meta']['status'] = 400

            # TODO: Check form validation errors and replace content

            response_content['meta']['errors'] = self.errors
            response_content['data'] = self.data
            response_content = json.dumps(response_content)
        else:
            response_content = self.response.content

        return response_content

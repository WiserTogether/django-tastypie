class DefaultEnvelope(object):
    def __init__(self, request_type, response):
        self.request_type = request_type
        self.response = response

    def transform(self):
        return self.response


class MetaEnvelope(DefaultEnvelope):
    def __init__(self, request_type, response):
        super(MetaEnvelope, self).__init__(request_type, response)
        self.status = 200
        self.errors = {}
        self.data = {}

    def transform(self):
        pass

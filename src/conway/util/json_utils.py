import json                                             as _json


class JSON_Utils():

    '''
    Class used to aggregate a number of helper methods to manipulate strings and files adhering to the JSON format.
    '''
    def __init__(self):
        pass

    def nice(json_content: str|list|dict):
        '''
        Returns a nice rendering of a JSON object that can then be displayed to an end-user.
        It is "nice" because it uses indentation to reflect nested structures, and uses a new line for
        each field.

        :param str|list|dict json_object: JSON-formatted data
        :returns: a nice string represention or `json_content`
        :rtype: str
        '''
        if type(json_content) == str:
            json_object                         = _json.loads(json_content)
        else:
            json_object                         = json_content

        json_formatted_str                      = _json.dumps(json_object, indent=2)
        return json_formatted_str
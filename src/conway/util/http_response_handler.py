class HTTP_ResponseHandler():

    '''
    Helper class to process HTTP responses, based on the status code of the response.

    This class is expected to be extended, so that derived classes can cater to specific use cases by first
    catching specific status codes that are meaningful to each use case, before calling super() so that this
    class catches "everything else".
    '''
    def __init__(self):
        pass

    def process(self, response):
        '''
        :param requests.models.Response response: HTTP response object to process
        :returns: The payload of the response, if the handler considers the response successful. Otherwise
                the handler will raise an exception.
        :rtype: dict
        '''
        status                                              = response.status_code
        url                                                 = response.url
        data                                                = response.json()
        match status:
            case stat if 200 <= stat and stat <= 299:
                # This means success, in the case of a POST
                return data
            case 401:
                certificate_file                        = f"<YOUR CONDA INSTALL ROOT>/envs/<YOUR CONDA ENVIRONMENT>/lib/site-packages/certifi/cacert.pem"
                            
                raise ValueError(f"Error status {response.status_code} from HTTP request to '{url}'."
                            + f"\nThis often happens due to one of three things: "
                            + f"\n\t1) expired GitHub certificates (most common)"
                            + f"\n\t2) or expired GitHub token in the secrets file for conway.ops"
                            + f"\n\t3) or something else."
                            + f"\n\nFor the first, if using Conda, check {certificate_file}"
                            + f"\n\nFor the second, login to GitHub as a user with access to the remote repos in question"
                            + f"\nand generate a token (in settings=>developer settings) and copy it to the secrets file for this repo."
                            + f"\n\nFor the third, this was the HTTP response: \n{data}")  
            case _:         
                raise ValueError(f"Error status {response.status_code} from doing: POST on '{url}'."
                             + f"\n\nThis was the HTTP response: \n{data}")  




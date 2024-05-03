

class CommandParser():
    '''
    Utility class used to correctly parse strings that correspond to CLI commands
    


    '''
    def __init__(self):
        pass
    
    def get_argument_list(self, command):
        '''
        Tokenizes a CLI command and returns its underlying argument list, with particular support for the "tricky case" when 
        a command includes arguments with spaces surrounded in quotes.

        For example, given the command

                'git commit -m "[task-conway-2] Set up branch management preliminaries"'

        the correct argument list (and what is returned by this method) would be:

            ['git',
            'commit',
            '-m',
            '"[task-conway-2] Set up branch management preliminaries"']

        and not 

            ['git',
            'commit',
            '-m',
            '"[task-conway-2]',
            'Set',
            'up',
            'branch',
            'management',
            'preliminaries"']

        :param str command: CLI command to tokenize
        :return: argument list for the command
        :rtype: list[str]
        '''
        # The comments below explain the algorithm with the example where the command is
        #
        #           'git commit -m "[task-conway-2] Set up branch management preliminaries"'
        #
        SPACE                                   = " "
 
        # On a first pass, we tokenize by space, even if splits a single argument like 
        # "[task-conway-2] Set up branch management preliminaries" into pieces.
        tokens                                  = command.split(SPACE)

        '''
        So now tokens is something like this, and we want to traverse the token and recombine together
        the ones that belong to a common argument. In this example, we want to re-combine tokens wit index 3+ into a single string.
                    ['git',
                    'commit',
                    '-m',
                    '"[task-conway-2]',
                    'Set',
                    'up',
                    'branch',
                    'management',
                    'preliminaries"']

        The algorithm is to use a state machine with two states. The machine will traverse the tokens one at a time,
        and the logic to examine a token is dependent on which state the machine is in.

        The two states are:

        * CompositeArgumentState: represents the condition of already having entered a consecutive groups of tokens that
                            are part of the same substring.

        * _UsualState: represents the condition of not having yet entered a token that might be part of a bigger substring.
        
        Each state handles the next token, and if appropriate, transition to the other state if needed.

        '''
        machine                                 = self._StateMachine(tokens)
        machine.run()
        return machine.args


    class _StateMachine():

        SUBSTRING_DELIMETERS = ["'", "\""]

        def __init__(self, token_list):
            self.token_list                     = token_list
            self.token_idx                      = 0
            self.state                          = self._UsualState(machine=self)
            self.args                           = []

        def run(self):
            '''
            Progress one token
            '''
            while self.token_idx < len(self.token_list):
                self.state.advance()
            
        class _AbstractState():
            def __init__(self, machine):
                self.machine                    = machine
                self.next_token                 = None

            def advance(self):
                M                               = self.machine
                self.next_token                 = M.token_list[M.token_idx]
                M.token_idx                     += 1

        class CompositeArgumentState(_AbstractState):

            '''
            Represents the state where we are traversing a "composite argument", i.e., a collection of tokens
            like

            "[task-conway-2] Set up branch management preliminaries"

            that is surrounded by quotes, where the collection as a whole corresponsd to one argument, even
            if it is composed of multiple tokens.

            This class processes the tokens that comprise a composite, aggregating them into a string that
            represents the composite argument.
            '''
            def __init__(self, machine, initial_token):
                super().__init__(machine)
                self.next_token                 = initial_token[1:] # Don't include the quote at start of the composite
                self.delimeter                  = initial_token[0]

                # GOTCHA:
                #   There is a boundary case where there the composite consists of just one token.
                #   In that case, we are already at the last token, so need to make the same check that self.advance() makes
                #   to close things, since otherwise we would be skipping this last token (i.e., the composite
                #   argument would be missed entirely).
                #
                if self.at_composite_end():
                    self.argument_so_far        = None
                    self.close_composite()    
                else:       
                    self.argument_so_far        = self.next_token

            def advance(self):
                super().advance()
                if len(self.next_token.strip()) == 0:
                    return # Ignore the token
                elif self.at_composite_end():
                    self.close_composite()
                else:
                    self.augment_argument()
                
            def close_composite(self):
                M                               = self.machine

                to_be_added                     = self.next_token[:-1] # Don't include the quote at the end of composite
                if self.argument_so_far is None:
                    self.argument_so_far        = to_be_added
                else:
                    self.argument_so_far        += " " + to_be_added
                M.args.append(self.argument_so_far)
                M.state                         = M._UsualState(M)
            
            def augment_argument(self):
                self. argument_so_far += " " + self.next_token 

            def at_composite_end(self):
                if self.next_token[-1]==self.delimeter:
                    return True
                else:
                    return False
                
        class _UsualState(_AbstractState):

            '''
            Representes the "usual" state of the state machine, in which one token corresponds to one argument.

            As each token is processed, it will detect if a token is the start of a composite argument, in which
            case it will transition to that state.
            '''
            def __init__(self, machine):
                super().__init__(machine)

            def advance(self):
                super().advance()
                if len(self.next_token.strip()) == 0:
                    return # Ignore the token
                elif self.at_composite_start():
                    self.start_composite()
                else:
                    self.add_arg()

            def start_composite(self):
                M                               = self.machine
                M.state                         = M.CompositeArgumentState(M, self.next_token)
            
            def add_arg(self):
                M                               = self.machine
                M.args.append(self.next_token) 

            def at_composite_start(self):
                M                               = self.machine
                if self.next_token[0] in M.SUBSTRING_DELIMETERS:
                    return True
                else:
                    return False

    
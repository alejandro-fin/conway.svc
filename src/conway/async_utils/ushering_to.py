import asyncio

class UsheringTo():

    '''
    This class is an asynchronous context manager to provide syntactic sugar to "fork-join" situations,
    where computation must be parallelized across multiple coroutines, and then the results all collected
    at the end.

    For example, consider the following code snippet that defines a dictionary of 3 coroutines, and then
    uses this class in a for loop where each cycle ushers one of the 3 coroutines:

    .. code:

        async def A(prefix="") -> str:
            name = f"{prefix}A"
            print(f"{name} starts ...", flush=True)
            await asyncio.sleep(1)
            print(f"... {name} ends", flush=True)
            return f"{name}"    

        async def B(prefix="") -> str:
            name = f"{prefix}B"
            print(f"{name} starts ...", flush=True)
            x = await A(f"{name}->")
            print(f"... {name} ends", flush=True)
            return f"{name}"     

        async def C(prefix="") -> str:
            name = f"{prefix}C"
            print(f"{name} starts ...", flush=True)
            x = await B(f"{name}->")
            print(f"... {name} ends", flush=True)
            return f"{name}"       

        result_l = []
        work_dict = {"a": A, "b": B, "c": C}

        async with UsheringTo(result_l) as usher:
            for key in work_dict.keys():
                usher += work_dict[key]()
                
        result_l

    If you run the code above in Jupyter Notebook, you will get a result like this.
    
    NB 1: In Jupyter Notebook there is already an event loop, so the code above will work even if there is no
            call to start an event loop (i.e., no call like `return asyncio.run(supervisor()))` where `supervisor`
            would be a function wrapping the statement with UsheringTo:

    .. code::

        async def supervisor():
            result_l = []
            work_dict = {"a": A, "b": B, "c": C}

            async with UsheringTo(result_l) as usher:
                for key in work_dict.keys():
                    usher += work_dict[key]()
                    
            return result_l        
     
    NB 2: the order may vary, since we are in asynchronous, non-deterministic situation:

    .. code:: 
        B starts ...
        B->A starts ...
        C starts ...
        C->B starts ...
        C->B->A starts ...
        A starts ...
        ... B->A ends
        ... B ends
        ... C->B->A ends
        ... C->B ends
        ... C ends
        ... A ends
        ['B', 'C', 'A']

    :param list result_l: A (probably empty) list to which the results from coroutines must be appended.

    '''
    def __init__(self, result_l):
        self.result_l                                   = result_l

    def __iadd__(self, coro):
        if not asyncio.iscoroutine(coro):
            raise ValueError(f"Expected a coroutine, but instead got a {type(coro)}")
        self.to_do.append(coro)
        return self

    async def __aenter__(self):
        self.to_do                                      = []
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        to_do_iter                                      = asyncio.as_completed(self.to_do)
        for coro in to_do_iter:
            coro_result                                 = await coro
            self.result_l.append(coro_result)
        return
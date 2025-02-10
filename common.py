def successify(data):
    """
    Create a success response with provided data.
    
    Args:
        data (Any): Data to be returned in successful response
    
    Returns:
        dict: Standardized success response
    """
    return {
        "success": True,
        "error": False,
        "data": data
    }

def errorify(err):
    """
    Create an error response with provided error message.
    
    Args:
        err (str): Error message describing the failure
    
    Returns:
        dict: Standardized error response
    """
    return {
        "success": False,
        "error": err,
        "data": None
    }

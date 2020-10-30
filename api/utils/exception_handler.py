from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """
    Try to standardize error messages.
    Return dict with status_code and error_message keys
    """
    # Get the standard error response from DRF
    response = exception_handler(exc, context)

    if response is not None:
        if "detail" in response.data:
            message = response.data.pop("detail")
        elif "non_field_errors" in response.data:
            message = response.data.pop("non_field_errors")
        else:
            message = response.data

        data = {"error_message": message, "status_code": response.status_code}
        response.data = data
    return response

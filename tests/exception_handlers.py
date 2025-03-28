from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic_core import ValidationError as PydanticCoreValidationError

# Handle raw Pydantic v2 errors from Depends(BaseModel)
# This is needed because FastAPI's test client doesn't automatically convert Pydantic v2 validation errors
# into proper 422 responses like it does in production. By adding this handler, we ensure our tests
# match the production behavior where validation errors are returned as 422 responses with proper error details.
async def pydantic_core_validation_exception_handler(request, exc: PydanticCoreValidationError):
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder({"detail": exc.errors()}),
    ) 
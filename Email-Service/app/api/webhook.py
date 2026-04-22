import resend
import orjson

from fastapi.exceptions import HTTPException
from fastapi import Request, Response, APIRouter, status

from app.core.config import settings
from app.db.async_session import AsyncSessionDep
from app.repository.email import email_repository

webhook_router = APIRouter()


@webhook_router.post("/resend", status_code=status.HTTP_200_OK)
async def resend_webhook_receiver(request: Request, db: AsyncSessionDep) -> Response:
    """Endpoint to receive webhook callbacks from Resend."""
    payload = await request.body()
    payload_str = payload.decode()

    svix_id = request.headers.get("svix-id")
    svix_timestamp = request.headers.get("svix-timestamp")
    svix_signature = request.headers.get("svix-signature")

    if not all([svix_id, svix_timestamp, svix_signature]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing webhook headers"
        )

    webhook_secret = settings.RESEND_WEBHOOK_SECRET
    if not webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured",
        )

    try:
        resend.Webhooks.verify(
            {
                "payload": payload_str,
                "headers": {
                    "id": svix_id,
                    "timestamp": svix_timestamp,
                    "signature": svix_signature,
                },
                "webhook_secret": webhook_secret,
            }
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook verification failed",
        )

    try:
        event = orjson.loads(payload_str)
        event_type = event.get("type")
        event_data = event.get("data", {})
        to_email = event_data.get("to")[0] if event_data.get("to") else None
        print(f"Received webhook event: {event_type}")

        if event_type == "email.delivered":
            print(f"Email delivered successfully to {to_email}")

        elif event_type == "email.bounced":
            print(f"Email bounced for {to_email}")
            # upsert email into blacklist with reason to block future emails to the same email
            await email_repository.upsert_email_blacklist(
                db=db, email=to_email, reason="Email Bounced"
            )
            # TODO: update email log status and error info if email log exists for the bounced email

        elif event_type == "email.complained":
            print(f"Email marked as spam for {to_email}")
            # upsert email into blacklist with reason to block future emails to the same email
            await email_repository.upsert_email_blacklist(
                db=db, email=to_email, reason="Email Complained as Spam"
            )
            # TODO: update email log status and error info if email log exists for the complained email

        else:
            print(f"Unhandled event type: {event_type}")

        return Response(content="Webhook received", status_code=status.HTTP_200_OK)

    except Exception as ex:
        print(
            f"Error processing webhook payload for email: {to_email}, error: {str(ex)}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to process webhook"
        )

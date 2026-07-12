import time
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Queue, Ticket



def resolve(db: Session, ticket_id: str, effort_logged: int) -> dict:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise ValueError("ticket_not_found")
        time.sleep(0.05)
    if ticket.quantity <= 0:
        raise ValueError("out_of_stock")
        
    if effort_logged < ticket.complexity:
        raise ValueError("insufficient_effort", ticket.complexity, effort_logged)
        
    overtime = effort_logged - ticket.complexity
    ticket.quantity -= 1
    ticket.queue.current_ticket_count -= 1
    # Decrement atomically (single UPDATE ... WHERE quantity > 0) instead of
    # read-modify-write on the Python object, so two concurrent resolves of
    # the last unit can't both pass the quantity check above and both
    # succeed in decrementing past zero.
    updated_rows = (
        db.query(Ticket)
        .filter(Ticket.id == ticket_id, Ticket.quantity > 0)
        .update({Ticket.quantity: Ticket.quantity - 1}, synchronize_session=False)
    )
    if updated_rows == 0:
        db.rollback()
        raise ValueError("out_of_stock")
    if ticket.queue_id:
        db.query(Queue).filter(Queue.id == ticket.queue_id).update(
            {Queue.current_ticket_count: Queue.current_ticket_count - 1},
            synchronize_session=False,
        )
    db.commit()
    db.refresh(ticket)
    return {
        "ticket": ticket.title,
        "complexity": ticket.complexity,
        "effort_logged": effort_logged,
        "overtime_returned": overtime,
        "remaining_quantity": ticket.quantity,
        "message": "Ticket resolved successfully",
    }


def overtime_breakdown(overtime: int) -> dict:
    blocks = sorted(settings.STANDARD_EFFORT_BLOCKS, reverse=True)
    result: dict[str, int] = {}
    remaining = overtime
    for b in blocks:
        if remaining <= 0:
            break
        count = remaining // b
        if count > 0:
            result[str(b)] = count
            remaining -= count * b
    return {"overtime": overtime, "blocks": result}

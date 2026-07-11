# MVP Scope: Scheduling Tool for Therapists

## Problem

Therapists need a simple, professional booking system that lets clients self-schedule, reduces no-shows, and integrates with their existing calendar. Calendly and similar tools are generic — they don't address therapist-specific needs like session-length defaults, waitlists, or insurance/telehealth considerations.

## Target User

Solo or small-practice therapists (psychologists, counselors, social workers, life coaches) who currently schedule via phone, email, or text. They are not technical. They value simplicity, reliability, and professionalism.

## MVP Definition

The MVP is a single-page scheduling link that therapists share with clients. Clients pick a slot, confirm, and the booking syncs to the therapist's calendar. That's the core loop. Everything else is out of scope for v1.

### In Scope (MVP)

1. **Therapist onboarding**
   - Sign up with email + password
   - Set name, title, practice name
   - Set a default session length (30/45/50/60 min)
   - Set available hours (days of week, start/end time)
   - Add a buffer between appointments (e.g., 15 min)

2. **Calendar sync**
   - Connect a Google Calendar (OAuth)
   - Block off booked slots automatically
   - Show conflicts with existing calendar events
   - Two-way sync: bookings appear on Google Calendar, blocked calendar events block booking slots

3. **Booking link**
   - Unique URL per therapist (e.g., `app.example.com/therapist-id`)
   - Public page showing available slots for next 7 days
   - Client enters name, email, phone (optional), reason for visit (optional)
   - Confirmation email to client and therapist

4. **Booking management**
   - Therapist sees upcoming appointments in a list
   - Therapist can cancel or reschedule a booking
   - Client receives email with cancellation/reschedule link

5. **Basic notifications**
   - Confirmation email on booking
   - Reminder email 24 hours before appointment
   - Cancellation notification email

### Out of Scope (Post-MVP)

- Payment collection / Stripe integration
- Telehealth video integration
- Insurance / billing / invoicing
- Client portal (clients log in to manage their own appointments)
- Waitlist / open slot features
- SMS / text reminders
- Multiple therapists / team scheduling
- Custom branding / white-label
- Advanced analytics
- iOS/Android native apps
- Offline mode
- HIPAA compliance / BAA (this is a business decision, not a technical feature — see Risk section)

## Technical Approach

### Stack

- **Frontend**: Next.js (App Router) + React + Tailwind CSS
- **Backend**: Next.js API routes (serverless)
- **Database**: PostgreSQL (Neon or Supabase)
- **ORM**: Prisma
- **Auth**: Clerk or NextAuth (email + password, with magic link as secondary)
- **Calendar**: Google Calendar API (OAuth2)
- **Email**: Resend or SendGrid
- **Hosting**: Vercel
- **Deployment**: Single monorepo, single deploy target

### Data Model (core tables)

```
User          -- therapist account (name, email, password hash, practice info)
CalendarSync  -- Google OAuth tokens, calendar ID
Availability  -- therapist's recurring availability (day of week, start/end, buffer)
Booking       -- client booking (client name, email, phone, start, end, status, reason)
Event         -- synced Google Calendar event ID (for two-way sync)
```

### Key Flows

1. **Onboarding**: Sign up -> configure availability -> connect Google Calendar -> get booking link
2. **Client books**: Visit link -> pick slot -> fill form -> confirm -> emails sent -> calendar updated
3. **Reminder**: Cron job runs nightly, sends emails for next-day appointments
4. **Cancellation**: Therapist or client clicks cancel link -> booking deleted -> calendar unblocked -> emails sent

## Success Criteria for MVP

- A therapist can sign up, configure availability, connect their calendar, and share their link within 5 minutes
- A client can book an appointment without creating an account
- Bookings appear on the therapist's Google Calendar within 30 seconds
- Confirmation and reminder emails are delivered within 2 minutes
- Therapist can see and manage upcoming appointments from the dashboard

## Risks and Open Questions

1. **HIPAA compliance**: Client name, email, and appointment time in email subjects may constitute PHI. If the MVP handles PHI, a BAA with email provider and Google may be required. Recommendation: keep the MVP as a general scheduling tool (no clinical notes, no insurance data) and position it as non-PHI until the business decides otherwise. Add a disclaimer on the booking page.

2. **Google Calendar API limits**: Rate limits are generous for a solo-therapist use case, but conflict resolution needs to be robust. Use Google's free/busy API to check availability before confirming.

3. **Time zones**: Therapists and clients may be in different time zones. Default to therapist's local time, show client's local time on the booking page.

4. **No-shows**: Not in MVP scope, but a high-priority post-MVP feature. Track "attended" vs "no-show" manually for now.

## Phased Plan

### Phase 1: Core Booking (Weeks 1-3)
- User auth + onboarding flow
- Availability configuration UI
- Google Calendar OAuth + sync
- Booking page + client form
- Confirmation emails

### Phase 2: Management + Reminders (Weeks 4-5)
- Therapist dashboard (upcoming bookings list)
- Cancel/reschedule flow
- 24-hour reminder emails
- Basic error handling + edge cases

### Phase 3: Polish + Launch (Weeks 6-7)
- UI polish + mobile responsiveness
- Testing (end-to-end booking flow)
- Landing page for marketing
- Soft launch to 5-10 beta therapists

### Phase 4: Post-MVP Priorities (Weeks 8+)
- Payment collection
- SMS reminders
- Client portal
- Waitlist / open slots
- HIPAA readiness
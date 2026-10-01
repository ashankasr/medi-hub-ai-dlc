# ADR-0008: Notification providers: Brevo for email, Firebase for push

- **Status:** Accepted
- **Date:** 2026-10-01
- **Deciders:** Project owner
- **Serves:** Driver "EU, GDPR"; architecture §2.6, §3.1 (Notifications module)

## Context

Staff and patients need email and mobile push notifications (appointment
reminders, task alerts, account flows). Both channels leave our control: email
passes through third-party mail systems, and push goes through Apple and Google
infrastructure. The product targets EU hospital groups.

## Decision

- **Email:** **Brevo** in production.
- **Push:** **Firebase Cloud Messaging (FCM)** for Android and iOS.
- Both sit behind **provider-neutral interfaces** in the Notifications module,
  so a provider can be replaced without touching other modules.
- **No clinical data** in any notification content: send a link or a prompt
  to open the app.
- **Personal data excluded by default.** Exceptions are decided per
  notification type (for example, a first name in an email greeting).
- Development uses non-delivering stand-ins (proposed: Mailpit for email, a
  logging push sender by default).

## Alternatives considered

- **Other email services (e.g. Azure Communication Services, SendGrid)** —
  Brevo chosen; it is an EU-based provider.
- **APNs directly / Azure Notification Hubs for push** — FCM covers both
  platforms through one API and fits the Expo toolchain.

## Consequences

**Positive**

- Providers can be swapped behind the interfaces.
- The content rules keep health data out of third-party channels.

**Negative / costs**

- A data processing agreement is needed with each provider.
- FCM is a US-owned service; this is acceptable only because payloads carry
  no clinical data and personal data is excluded by default.
- Device tokens must be stored and kept current per user and device.

**Open points**

- Personal-data exceptions, decided per notification type during grooming.

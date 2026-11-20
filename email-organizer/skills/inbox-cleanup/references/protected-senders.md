# Protected senders

Never bulk-trashed, whatever the mode or volume. Many send marketing and records from one domain:
unsubscribe the marketing address, keep the mail. **Unsure → keep.** Junk costs kilobytes.

| Category | Examples for Efaz | What's inside |
|---|---|---|
| Account security | Any OTP, sign-in alert, password reset, 2FA, recovery | Codes needed under time pressure. Never labelled, never trashed |
| Employer | bKash (work domain), HR, payroll | Payslips, letters, policies |
| Job applications | Employers and recruiters Efaz applied to, BDjobs/LinkedIn application notices | Interview calls, offers, rejections |
| Financial | Banks, cards, MFS (bKash, Nagad, Rocket), brokerages, remittance | Statements, transactions, tax |
| Government and legal | NBR, passport, NID, courts, e-signing | Deadlines, reference numbers |
| Education | University, exam boards, certifications | Certificates, transcripts, results |
| Health and insurance | Hospitals, clinics, insurers | Reports, claims, appointments |
| Utilities and bills | DESCO, DPDC, Titas, WASA, ISP, mobile operators | Bills: often the only proof of address |
| Orders and travel | Daraz, Foodpanda, Pathao, airlines, bus and hotel bookings | Receipts, tracking, tickets |
| Personal | Any free-mail address, anyone Efaz has replied to | Never bulk-trash, never unsubscribe |

Content words that mark a message protected (also in `config/rules.default.json`):
`statement invoice bill payslip salary receipt order tracking refund tax policy claim contract
booking itinerary e-ticket otp verification password security alert interview offer`

Rescue sweep before emptying Trash:

```
in:trash from:(<domain>) (bill OR invoice OR payslip OR statement OR receipt OR tax OR otp OR interview)
```

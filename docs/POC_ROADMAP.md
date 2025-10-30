# POC Development Roadmap

## Timeline: 1 Week Sprint

**Goal:** Demonstrate working email classification system with OAuth authentication, Graph API integration, and Azure OpenAI categorization.

**Target Demo Date:** [Set your date]

---

## Phase 1: Foundation & Documentation (Day 1)

### Documentation Setup
- [x] Create `docs/` folder structure
- [x] Write API_SPEC.md
- [x] Write CLASSIFICATION_SPEC.md
- [x] Write POC_ROADMAP.md (this file)
- [x] Write ARCHITECTURE.md
- [x] Write TESTING.md

### Project Setup
- [x] Review existing code
- [x] Verify all environment variables in `.env`
- [x] Test OAuth authentication
- [x] Confirm Azure OpenAI Service credentials are valid

### Initial FastAPI App
- [x] Create `src/main.py` with FastAPI initialization
- [x] Add `/health` endpoint
- [x] Test with `uvicorn src.main:app --reload`
- [x] Confirm health check returns 200 OK

**Estimated Time:** 2-3 hours
**Success Criteria:** `curl http://localhost:8000/health` returns `{"status": "ok"}`

---

## Phase 2: OAuth Authentication (Day 2-3)

### Environment Configuration
- [x] Add `REDIRECT_URI` to `.env`
- [x] Update Azure app registration redirect URIs in Entra ID portal
- [x] Document redirect URI changes in README

### ConfidentialClientApplication Setup
- [x] Import MSAL `ConfidentialClientApplication`
- [x] Create auth configuration from environment variables
- [x] Add global dict for token storage: `user_tokens = {}`

### /auth/login Endpoint
- [x] Generate auth URL with MSAL
- [x] Add state parameter for CSRF protection
- [x] Store state in session/memory
- [x] Return redirect response to Microsoft

### /auth/callback Endpoint
- [x] Validate state parameter
- [x] Exchange authorization code for tokens
- [x] Extract `access_token`, `refresh_token`, `expires_in`
- [x] Store tokens in `user_tokens` dict (use demo_user for POC)
- [x] Redirect to dashboard (`/`)

### Testing Authentication
- [x] Visit `http://localhost:8000/auth/login` in browser
- [x] Complete Microsoft sign-in
- [x] Verify redirect to callback
- [x] Check token stored in memory
- [x] Handle authentication errors gracefully

**Estimated Time:** 4-6 hours
**Success Criteria:** Can authenticate via browser and see stored token in logs

---

## Phase 3: Microsoft Graph Integration (Day 3-4)

### Graph API Helper Functions
- [x] Create `src/graph.py` module
- [x] Add `get_messages(access_token, top=10, folder)` function
- [x] Use `httpx` to call `/me/mailFolders/{folder}/messages` endpoint
- [x] Parse and format response JSON
- [x] Handle 401 errors (expired token)

### /graph/fetch Endpoint
- [x] Accept `top`, `skip`, `folder` query parameters
- [x] Retrieve access token from `user_tokens`
- [x] Call `get_messages()` helper
- [x] Return formatted JSON response
- [x] Add error handling for missing token

### Token Validation
- [x] Check token expiration before Graph API calls
- [x] Return 401 with redirect to `/auth/login` if expired
- [x] Log token usage for debugging

### Testing Graph Integration
- [x] Authenticate via `/auth/login`
- [x] Call `/graph/fetch?top=5`
- [x] Verify emails returned in response
- [x] Test with different `top` values and folders
- [x] Verify error handling when not authenticated

### Testing Infrastructure
- [x] Create test email generation script
- [x] Add support for drafts folder (for testing with mock senders)
- [x] Add `--save-to-drafts` and `--no-metadata` flags

**Estimated Time:** 3-4 hours
**Success Criteria:** Can fetch and display email list via API endpoint

---

## Phase 4: Azure OpenAI Classification (Day 4-5)

### Azure OpenAI Setup
- [x] Install/verify OpenAI Python SDK (with Azure support)
- [x] Create `src/classifier.py` module (future)
- [x] Add Azure OpenAI client initialization
- [x] Define preset categories list

### Prompt Engineering
- [ ] Implement system prompt from CLASSIFICATION_SPEC.md
- [ ] Create user prompt template
- [ ] Add input sanitization (HTML stripping, truncation)
- [ ] Test prompt with sample emails manually

### classify_email() Function
- [x] Build complete Azure OpenAI Service request
- [x] Set temperature=0.3, max_tokens=200
- [x] Force JSON response format
- [x] Parse response and extract category/confidence
- [x] Add error handling and fallback logic

### /classify Endpoint
- [x] Accept POST request with email data
- [x] Validate required fields (subject, body, from)
- [x] Call `classify_email()` function
- [x] Return classification result as JSON
- [x] Handle Azure OpenAI Service errors

### Testing Classification
- [x] Create test email samples (18 emails covering all 6 categories)
- [x] Call `/classify` for each test email
- [x] Verify correct categories returned
- [x] Check confidence scores are reasonable (>0.7)
- [x] Test edge cases (empty body, no subject, etc.)

**Estimated Time:** 4-5 hours
**Success Criteria:** Can classify individual emails with >85% accuracy on test set
**Status:** ✅ COMPLETED - Azure OpenAI Service integrated and working!

---

## Phase 5: Automated Processing (Day 5-6)

### Storage Layer (In-Memory)
- [ ] Create `processed_emails` dict: `{message_id: {category, timestamp, confidence}}`
- [ ] Add `last_check_time` global variable
- [ ] Add helper functions: `mark_processed()`, `is_processed()`

### /inbox/process-new Endpoint
- [ ] Fetch emails newer than `last_check_time`
- [ ] Filter out already processed emails (by `internetMessageId`)
- [ ] Loop through unprocessed emails
- [ ] Classify each email
- [ ] Store results in `processed_emails`
- [ ] Update `last_check_time`
- [ ] Return summary statistics

### Idempotency
- [ ] Ensure same email isn't processed twice
- [ ] Use `internetMessageId` as unique identifier
- [ ] Add deduplication logic

### Testing Automated Processing
- [ ] Authenticate and fetch initial emails
- [ ] Call `/inbox/process-new` - should process all
- [ ] Call again immediately - should process 0 (all already processed)
- [ ] Send yourself a new test email
- [ ] Call `/inbox/process-new` - should process 1
- [ ] Verify stats are accurate

**Estimated Time:** 3-4 hours  
**Success Criteria:** Can automatically process new emails without duplicates

---

## Phase 6: Simple Dashboard (Day 6)

### HTML Template
- [ ] Create `templates/` folder
- [ ] Create `dashboard.html` with Jinja2 template
- [ ] Add basic CSS styling (or use CDN like Tailwind)

### Dashboard Endpoint (/)
- [ ] Check if user is authenticated
- [ ] If not, show "Login" button → `/auth/login`
- [ ] If authenticated, fetch processed emails
- [ ] Group emails by category
- [ ] Render `dashboard.html` with email data

### Dashboard Features
- [ ] Display email count per category
- [ ] List recent emails (subject, from, category, confidence)
- [ ] Add "Process New Emails" button → calls `/inbox/process-new`
- [ ] Show last check time
- [ ] Add logout button (clears token)

### Testing Dashboard
- [ ] Visit `http://localhost:8000/` when not logged in
- [ ] Click login button and authenticate
- [ ] Verify email list displays correctly
- [ ] Click "Process New" button
- [ ] Verify page updates with new classifications

**Estimated Time:** 3-4 hours  
**Success Criteria:** Functional web UI showing classified emails

---

## Phase 7: Polish & Testing (Day 7)

### Error Handling Review
- [ ] Add try-catch blocks to all endpoints
- [ ] Return consistent error JSON format
- [ ] Add logging for debugging
- [ ] Test error scenarios (network failure, API limits, etc.)

### Documentation Updates
- [ ] Update README.md with setup instructions
- [ ] Add screenshots to documentation
- [ ] Document known limitations
- [ ] Add troubleshooting section

### End-to-End Testing
- [ ] Fresh start: Clear tokens, restart server
- [ ] Complete full flow: Login → Fetch → Classify → Display
- [ ] Test with different email types
- [ ] Verify all categories work correctly
- [ ] Check classification accuracy

### Demo Preparation
- [ ] Prepare demo script
- [ ] Create sample emails for demo
- [ ] Take screenshots/screen recording
- [ ] Prepare talking points (architecture, future plans)

**Estimated Time:** 2-3 hours  
**Success Criteria:** Smooth demo from start to finish, no crashes

---

## Optional Enhancements (If Time Permits)

### Backfill Feature
- [ ] Add `/inbox/backfill` POST endpoint
- [ ] Implement batch processing with progress tracking
- [ ] Add rate limiting to avoid API throttling
- [ ] Create simple progress UI

### Logging & Analytics
- [ ] Add request logging
- [ ] Track classification accuracy over time
- [ ] Create simple stats endpoint

### Deployment Prep
- [ ] Create `requirements.txt` with pinned versions
- [ ] Add `Procfile` or startup command
- [ ] Document Azure App Service deployment steps

---

## Definition of Done (POC MVP)

Must Have:
- ✅ `/health` returns 200 OK
- ✅ `/auth/login` redirects to Microsoft, callback stores token
- ✅ `/graph/fetch` returns email list from Graph API
- ✅ `/classify` returns accurate category for single email
- ✅ `/inbox/process-new` auto-classifies new emails
- ✅ Web dashboard displays classified emails by category
- ✅ No crashes during normal operation

Nice to Have:
- 🎯 >85% classification accuracy
- 🎯 Clean, readable code with comments
- 🎯 Updated documentation with screenshots
- 🎯 Deployed to Azure (or ready to deploy)

---

## Blockers & Risks

### Known Issues
- **Token refresh not implemented:** Users will need to re-login when token expires (~1 hour)
- **Single-user only:** Token storage doesn't support multiple users
- **No persistence:** Server restart clears all data

### Mitigation
- Document limitations clearly
- Plan Phase 2 to address these issues
- Focus on demonstrating core concept first

---

## Success Metrics

### Technical Metrics
- [ ] All endpoints return 2xx responses under normal conditions
- [ ] Classification latency <2 seconds per email
- [ ] Zero duplicate processing of emails
- [ ] Uptime >99% during testing

### User Experience Metrics
- [ ] Demo can be completed in <5 minutes
- [ ] Classification accuracy >85% on test set
- [ ] UI is intuitive (no instructions needed)

---

## Post-POC: Phase 2 Planning

After POC is validated, prioritize:

1. **Multi-user support** - Session management, user database
2. **Token refresh** - Implement refresh token flow
3. **Persistent storage** - Azure Table/Blob or SQLite
4. **User-defined categories** - UI for category management
5. **University deployment** - Align with IT-15 policy requirements
6. **Real @uiowa.edu testing** - Get Entra ID permissions

---

## Daily Check-In Questions

At end of each day, ask:
1. What did I complete today?
2. What's blocking me?
3. Am I on track for demo date?
4. Do I need help from teammates/Claude?

Keep momentum! 🚀
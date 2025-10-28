# POC Development Roadmap

## Timeline: 1 Week Sprint

**Goal:** Demonstrate working email classification system with OAuth authentication, Graph API integration, and OpenAI categorization.

**Target Demo Date:** [Set your date]

---

## Phase 1: Foundation & Documentation (Day 1)

### Documentation Setup
- [x] Create `docs/` folder structure
- [x] Write API_SPEC.md
- [x] Write CLASSIFICATION_SPEC.md
- [x] Write POC_ROADMAP.md (this file)
- [ ] Write ARCHITECTURE.md

### Project Setup
- [ ] Review existing code (`test_device_flow.py`)
- [ ] Verify all environment variables in `.env`
- [ ] Test existing device flow authentication
- [ ] Confirm OpenAI API key is valid

### Initial FastAPI App
- [ ] Create `app.py` with FastAPI initialization
- [ ] Add `/health` endpoint
- [ ] Test with `uvicorn app:app --reload`
- [ ] Confirm health check returns 200 OK

**Estimated Time:** 2-3 hours  
**Success Criteria:** `curl http://localhost:8000/health` returns `{"status": "ok"}`

---

## Phase 2: OAuth Authentication (Day 2-3)

### Environment Configuration
- [ ] Add `REDIRECT_URI` to `.env` (local: `http://localhost:8000/auth/callback`)
- [ ] Update Azure app registration redirect URIs in Entra ID portal
- [ ] Document redirect URI changes in README

### ConfidentialClientApplication Setup
- [ ] Import MSAL `ConfidentialClientApplication`
- [ ] Create auth configuration from environment variables
- [ ] Add global dict for token storage: `user_tokens = {}`

### /auth/login Endpoint
- [ ] Generate auth URL with MSAL
- [ ] Add state parameter for CSRF protection
- [ ] Store state in session/memory
- [ ] Return redirect response to Microsoft

### /auth/callback Endpoint
- [ ] Validate state parameter
- [ ] Exchange authorization code for tokens
- [ ] Extract `access_token`, `refresh_token`, `expires_in`
- [ ] Store tokens in `user_tokens` dict (use dummy user_id for POC)
- [ ] Redirect to dashboard (`/`)

### Testing Authentication
- [ ] Visit `http://localhost:8000/auth/login` in browser
- [ ] Complete Microsoft sign-in with `appliedai.demo@outlook.com`
- [ ] Verify redirect to callback
- [ ] Check token stored in memory (add debug logging)
- [ ] Handle authentication errors gracefully

**Estimated Time:** 4-6 hours  
**Success Criteria:** Can authenticate via browser and see stored token in logs

---

## Phase 3: Microsoft Graph Integration (Day 3-4)

### Graph API Helper Functions
- [ ] Create `graph.py` module
- [ ] Add `get_messages(access_token, top=10)` function
- [ ] Use `httpx` to call `/me/messages` endpoint
- [ ] Parse and format response JSON
- [ ] Handle 401 errors (expired token)

### /graph/fetch Endpoint
- [ ] Accept `top` query parameter (default=10)
- [ ] Retrieve access token from `user_tokens`
- [ ] Call `get_messages()` helper
- [ ] Return formatted JSON response
- [ ] Add error handling for missing token

### Token Validation
- [ ] Check token expiration before Graph API calls
- [ ] Return 401 with redirect to `/auth/login` if expired
- [ ] Log token usage for debugging

### Testing Graph Integration
- [ ] Authenticate via `/auth/login`
- [ ] Call `/graph/fetch?top=5`
- [ ] Verify emails returned in response
- [ ] Test with different `top` values
- [ ] Verify error handling when not authenticated

**Estimated Time:** 3-4 hours  
**Success Criteria:** Can fetch and display email list via API endpoint

---

## Phase 4: OpenAI Classification (Day 4-5)

### OpenAI Setup
- [ ] Install/verify OpenAI Python SDK
- [ ] Create `classifier.py` module
- [ ] Add OpenAI client initialization
- [ ] Define preset categories list

### Prompt Engineering
- [ ] Implement system prompt from CLASSIFICATION_SPEC.md
- [ ] Create user prompt template
- [ ] Add input sanitization (HTML stripping, truncation)
- [ ] Test prompt with sample emails manually

### classify_email() Function
- [ ] Build complete OpenAI API request
- [ ] Set temperature=0.3, max_tokens=200
- [ ] Force JSON response format
- [ ] Parse response and extract category/confidence
- [ ] Add error handling and fallback logic

### /classify Endpoint
- [ ] Accept POST request with email data
- [ ] Validate required fields (subject, body, from)
- [ ] Call `classify_email()` function
- [ ] Return classification result as JSON
- [ ] Handle OpenAI API errors

### Testing Classification
- [ ] Create test email samples (5-10 emails covering all categories)
- [ ] Call `/classify` for each test email
- [ ] Verify correct categories returned
- [ ] Check confidence scores are reasonable (>0.7)
- [ ] Test edge cases (empty body, no subject, etc.)

**Estimated Time:** 4-5 hours  
**Success Criteria:** Can classify individual emails with >85% accuracy on test set

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
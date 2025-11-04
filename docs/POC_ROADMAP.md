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
- [x] Confirm Azure OpenAI credentials are valid (now via AI Foundry)

### Initial FastAPI App
- [x] Create `src/main.py` with FastAPI initialization
- [x] Add `/health` endpoint
- [x] Test with `uvicorn src.main:app --reload`
- [x] Confirm health check returns 200 OK

**Estimated Time:** 2-3 hours
**Success Criteria:** `curl http://localhost:8000/health` returns `{"status": "ok"}`

---

## Phase 2: OAuth Authentication (Day 2-3) ✅ COMPLETED

### Environment Configuration
- [x] Create Azure App Registration: `app-appliedai-classifier-poc`
- [x] Configure single tenant authentication
- [x] Add `REDIRECT_URI` to `.env`
- [x] Update Azure app registration redirect URIs in Entra ID portal
- [x] Create client secret: `poc-local-dev` (24-month expiration)
- [x] Configure API permissions (Mail.Read, Mail.ReadWrite, offline_access)
- [x] Document redirect URI changes in README

### Client Secret Management
- [x] Store secret in `.env` file (gitignored)
- [x] Document secret description: `poc-local-dev`
- [x] Set calendar reminder for rotation (expires in 24 months)
- [ ] **Phase 8**: Migrate to Azure Key Vault

### OAuth Implementation
- [x] Import MSAL `ConfidentialClientApplication`
- [x] Create auth configuration from environment variables
- [x] Add global dict for token storage: `user_tokens = {}`
- [x] Implement state parameter for CSRF protection
- [x] Store tokens server-side (not in cookies)

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

### Azure AI Foundry / OpenAI Setup
- [x] Install/verify OpenAI Python SDK (with Azure support)
- [x] Create `src/classifier.py` module (future)
- [x] Add Azure OpenAI client initialization (compatible with AI Foundry)
- [x] Define preset categories list
- [x] **Migrated to Azure AI Foundry (2025-11-04)**

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

## Phase 5: Automated Processing (Day 5-6) ✅ COMPLETED 2025-10-31

### Azure AI Foundry Migration
- [x] Created AI Foundry Hub (aih-appliedai-classifier-poc)
- [x] Created AI Foundry Project (aip-appliedai-classifier-poc)
- [x] Deployed gpt-4o-mini model
- [x] Updated all documentation to reflect AI Foundry integration
- [x] Verified code compatibility (no changes needed!)

### Storage Layer (In-Memory)
- [x] Create `processed_emails` dict: `{message_id: {category, timestamp, confidence, subject, from}}`
- [x] Add `last_check_time` global variable
- [x] Add helper functions: `mark_processed()`, `is_processed()`, `get_processed_emails()`

### /inbox/process-new Endpoint
- [x] Fetch emails newer than `last_check_time` (or all on first run)
- [x] Filter out already processed emails (by `internetMessageId`)
- [x] Loop through unprocessed emails
- [x] Classify each email using Azure OpenAI
- [x] **Assign Outlook category to each email**
- [x] Store results in `processed_emails`
- [x] Update `last_check_time`
- [x] Return summary statistics with category distribution

### Idempotency
- [x] Ensure same email isn't processed twice
- [x] Use `internetMessageId` as unique identifier
- [x] Add deduplication logic
- [x] Safe to call multiple times

### Outlook Category Assignment (Bonus!)
- [x] Implement `assign_category_to_message()` in graph.py
- [x] GET current categories, add new one, PATCH email
- [x] Handle errors gracefully (continue on failure)
- [x] Categories appear as colored labels in Outlook

### Debug Endpoint
- [x] Add `/debug/processed` to view all processed emails
- [x] Returns count, last_check_time, and full email list

### Testing Automated Processing
- [x] Authenticate and fetch initial emails
- [x] Call `/inbox/process-new` - should process all
- [x] Call again immediately - should process 0 (all already processed)
- [x] Send yourself a new test email
- [x] Call `/inbox/process-new` - should process 1
- [x] Verify stats are accurate
- [x] Check Outlook for colored category labels

**Estimated Time:** 3-4 hours
**Actual Time:** ~4 hours
**Success Criteria:** ✅ Can automatically process new emails without duplicates
**Bonus:** ✅ Emails automatically tagged with Outlook categories!

---

## Phase 6: Web Dashboard (Day 6-7) ✅ COMPLETED 2025-11-04

### HTML Template
- [x] Create `templates/` folder
- [x] Create `dashboard.html` with Jinja2 template (~350 lines)
- [x] Add Tailwind CSS styling via CDN
- [x] Implement responsive design

### Dashboard Endpoint (/)
- [x] Check if user is authenticated
- [x] Show login screen if not authenticated
- [x] Fetch and process emails from memory if authenticated
- [x] Group emails by category
- [x] Calculate statistics (total, avg confidence, last check time)
- [x] Format last check time as relative ("Just now", "5m ago", etc.)
- [x] Get scheduler status
- [x] Render `dashboard.html` with all data

### Dashboard Features
- [x] **Stats Cards:** Total, last check, scheduler status, avg confidence
- [x] **Category Distribution:** 6 cards with emoji, count, description
- [x] **Email Lists:** Tables grouped by category (10 most recent per category)
- [x] **Action Bar:** Process button, debug link, auto-refresh checkbox
- [x] **Process Button:** JavaScript with loading state and error handling
- [x] **Auto-refresh:** Optional 30-second page reload
- [x] **Logout Button:** Clears token and returns to login
- [x] **Empty State:** Friendly message when no emails processed
- [x] **Color-coded Confidence:** Green (80%+), yellow (60-79%), red (<60%)

### Logout Endpoint
- [x] Add `GET /auth/logout` endpoint
- [x] Clear user token from memory
- [x] Redirect to dashboard (shows login screen)

### Testing Dashboard
- [x] Visit `http://localhost:8000/` when not logged in → Shows login screen
- [x] Click login button and authenticate → Shows full dashboard
- [x] Verify stats cards show correct data
- [x] Verify category distribution matches processed emails
- [x] Verify email lists display correctly with truncated subjects
- [x] Click "Process New" button → Shows loading, then success message
- [x] Verify page reloads after processing
- [x] Test auto-refresh checkbox → Page reloads after 30 seconds
- [x] Click logout → Returns to login screen

**Estimated Time:** 3-4 hours
**Actual Time:** ~3 hours
**Success Criteria:** ✅ Functional web UI with comprehensive stats and controls
**Status:** ✅ COMPLETE - Professional dashboard with University of Iowa branding!

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

## Phase 7: Performance Optimization (Future)

### Parallel Processing
- [ ] Implement asyncio-based parallel processing
- [ ] Add semaphore for rate limit control (5-10 workers)
- [ ] Use `asyncio.gather()` for concurrent classification
- [ ] Handle partial failures gracefully
- [ ] Add retry logic with exponential backoff

### Azure OpenAI Batch API
- [ ] Research Batch API for overnight processing
- [ ] Implement batch job submission
- [ ] Add status polling or webhook handlers
- [ ] Process 1000+ emails cost-effectively

### Azure AI Foundry Advanced Features
- [ ] Implement Prompt Flow for classification pipeline
- [ ] Set up evaluation datasets for accuracy testing
- [ ] Configure monitoring dashboards in AI Foundry
- [ ] Enable content safety filters
- [ ] Create A/B testing experiments for prompt optimization

### Persistent Storage
- [ ] Choose storage solution (Azure SQL, Table Storage, or Redis)
- [ ] Design database schema
- [ ] Implement database connection and ORM
- [ ] Migrate from in-memory to persistent storage
- [ ] Add database indexes for performance

### Performance Testing
- [ ] Benchmark current vs parallel performance
- [ ] Test with 10, 50, 100, 1000 emails
- [ ] Measure API rate limit impact
- [ ] Document performance improvements

**Target Improvements:**
- Sequential (current): 10 emails in ~20s
- Parallel (goal): 10 emails in ~5s (4x faster)
- Batch API: 1000 emails overnight (~50% cost savings)

**Estimated Time:** 1-2 weeks
**Success Criteria:**
- 4-5x speedup with parallel processing
- Persistent storage survives server restarts
- Can process 100+ emails efficiently

---

## Phase 8: Production Readiness (Future)

### Token Refresh
- [ ] Implement automatic token refresh using refresh_token
- [ ] Add token expiry monitoring
- [ ] Handle refresh token expiration gracefully
- [ ] Test token refresh flow

### Multi-User Support
- [ ] Add session management (Flask-Login or FastAPI-Users)
- [ ] Implement per-user storage (user_id in database)
- [ ] Add user registration/login flow
- [ ] Support user-specific category preferences

### Database Migration
- [ ] Set up Azure SQL Database or Table Storage
- [ ] Create migration scripts
- [ ] Add connection pooling
- [ ] Implement backup strategy

### Azure Deployment
- [ ] Create Azure App Service
- [ ] Configure environment variables in Azure
- [ ] Set up CI/CD pipeline (GitHub Actions)
- [ ] Add monitoring and logging (Application Insights)

### IT-15 Compliance
- [ ] Review University IT-15 policy requirements
- [ ] Implement multi-factor authentication (if required)
- [ ] Add audit logging
- [ ] Security review with IT team

**Estimated Time:** 2-3 weeks
**Success Criteria:**
- Multi-user system with authentication
- Deployed to Azure App Service
- Token refresh working automatically
- Meets university security requirements

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
- ✅ **Idempotency: Same email never processed twice**
- ✅ **Outlook category assignment works**
- ✅ `/debug/processed` shows all processed emails
- ✅ **Web dashboard displays classified emails by category**
- ✅ **Logout functionality works**
- ✅ No crashes during normal operation

Nice to Have:
- ✅ >85% classification accuracy (achieved with GPT-4o-mini)
- ✅ Clean, readable code with comments
- ✅ Updated documentation
- ✅ **Automated background scheduler**
- ✅ Test email generation script working
- 🎯 Deployed to Azure (Future: Phase 8)

**POC STATUS: ✅ COMPLETE (2025-11-04)**

All core POC features implemented and tested:
- **Phase 1-2:** Authentication with Microsoft Entra ID ✅
- **Phase 3:** Graph API email fetching ✅
- **Phase 4:** Azure OpenAI classification via AI Foundry ✅
- **Phase 5:** Automated batch processing with idempotency and Outlook categories ✅
- **Phase 6:** Professional web dashboard with stats and controls ✅

**Performance:**
- Classification: ~1.5-2.5s per email
- Dashboard load: <500ms
- Accuracy: >85% on test set
- Reliability: Zero duplicate processing

**Ready for demo and stakeholder review!** 🎉

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
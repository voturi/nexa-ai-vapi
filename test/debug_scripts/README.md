# Debug Scripts

This directory contains utility scripts for testing and debugging the multi-tenant AI receptionist system.

## Database Testing Scripts

### `check_tenants.py`
Check all tenants in the database and display their configuration.

```bash
python test/debug_scripts/check_tenants.py
```

### `create_sample_tenant.py`
Create a sample tenant (Mike's Plumbing) for testing purposes.

```bash
python test/debug_scripts/create_sample_tenant.py
```

### `verify_services.py`
Verify that tenant services are properly configured in the database.

```bash
python test/debug_scripts/verify_services.py
```

### `test_tenant_service.py`
Test the TenantService CRUD operations.

```bash
python test/debug_scripts/test_tenant_service.py
```

### `test_startup.py`
Test the application startup and database connectivity.

```bash
python test/debug_scripts/test_startup.py
```

## VAPI Phone Number Configuration Scripts

### `check_phone_config.py`
Check the current configuration of VAPI phone numbers.

```bash
python test/debug_scripts/check_phone_config.py
```

### `check_phone_status.py`
Detailed status check of all VAPI phone numbers including multi-tenant configuration status.

```bash
python test/debug_scripts/check_phone_status.py
```

### `create_phone_number.py`
Create a new phone number in VAPI with proper configuration.

```bash
python test/debug_scripts/create_phone_number.py
```

### `create_phone_unassigned.py`
Create a phone number without pre-assigned assistant (for multi-tenant pattern).

```bash
python test/debug_scripts/create_phone_unassigned.py
```

### `fix_phone_server_url.py`
Fix the server URL on a phone number to point to the correct webhook endpoint.

```bash
python test/debug_scripts/fix_phone_server_url.py
```

### `update_correct_phone.py`
Update phone number configuration to enable multi-tenant assistant-request pattern.

```bash
python test/debug_scripts/update_correct_phone.py
```

### `update_max_tokens.py`
Update the max tokens setting for VAPI assistant.

```bash
python test/debug_scripts/update_max_tokens.py
```

### `update_static_prompt.py`
Update the static system prompt for VAPI assistant.

```bash
python test/debug_scripts/update_static_prompt.py
```

## Quick Diagnostics

### Check if phone number is configured correctly for multi-tenant:
```bash
python test/debug_scripts/check_phone_status.py
```

Look for:
- ✅ Assistant ID: None (MULTI-TENANT MODE)
- ✅ Server URL: [your backend URL]/webhooks/vapi/call-started

### Check tenant data:
```bash
python test/debug_scripts/check_tenants.py
```

### Verify VAPI phone number configuration:
```bash
python test/debug_scripts/check_phone_config.py
```

## Notes

- All scripts assume you're running them from the backend root directory
- They will automatically load settings from your `.env` file
- Scripts that modify VAPI configuration require `VAPI_API_KEY` in your environment

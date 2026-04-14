
import datetime
import logging

def ensure_offset(dt_str):
    if not dt_str: return None
    # Check for T and absence of offset/Z
    if "T" in dt_str and "+" not in dt_str and "-" not in dt_str[dt_str.find("T"):] and "Z" not in dt_str:
        # Append Moscow offset if missing (user's timezone)
        return dt_str + "+03:00"
    return dt_str

def mock_add_event(summary, start_time, end_time=None, description=None):
    try:
        if not start_time:
            print(f"ERROR: Cannot create event '{summary}' without start_time")
            return

        # Normalize start_time
        start_time = ensure_offset(start_time)

        # If end_time is not provided, making it 1 hour after start_time
        if not end_time:
            # Parse start_time to calculate end_time
            try:
                # Clean Z for fromisoformat if needed
                parse_str = start_time.replace('Z', '+00:00')
                start_dt = datetime.datetime.fromisoformat(parse_str)
                end_dt = start_dt + datetime.timedelta(hours=1)
                end_time = end_dt.isoformat()
            except Exception as parse_err:
                print(f"WARNING: Could not parse start_time '{start_time}': {parse_err}")
                end_time = start_time
        else:
            end_time = ensure_offset(end_time)
        
        print(f"Success! Event: {summary}")
        print(f"  Start: {start_time}")
        print(f"  End:   {end_time}")
    except Exception as e:
        print(f"CRASH: {e}")

print("Testing empty start_time:")
mock_add_event("Test Empty", "")

print("\nTesting missing T (unsupported by LLM extraction usually, but good to test):")
mock_add_event("Test No T", "2024-04-14 15:00:00")

print("\nTesting valid ISO without offset:")
mock_add_event("Test ISO No Offset", "2024-04-14T15:00:00")

print("\nTesting valid ISO with Z:")
mock_add_event("Test ISO Z", "2024-04-14T15:00:00Z")

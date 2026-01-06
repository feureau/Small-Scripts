import sys
from internetarchive import search_items

def get_user_links(username):
    print(f"Fetching list for user: {username}...")
    print("This may take a moment depending on the number of uploads...")
    
    # Archive.org stores user uploads under the tag 'uploader'
    query = f"uploader:{username}"
    
    try:
        # search_items handles pagination automatically
        # fields=['identifier'] ensures we only fetch the ID, making it faster
        search = search_items(query, fields=['identifier'])
        
        count = 0
        for item in search:
            identifier = item['identifier']
            # Format as requested
            link = f"https://archive.org/compress/{identifier}"
            print(link)
            count += 1
            
        if count == 0:
            print(f"\nNo items found for user '{username}'.")
            print("Note: Ensure you are using the internal username (e.g., 'feureau') not the display name.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python archiveorg_user_extractor.py <username>")
        print("Example: python archiveorg_user_extractor.py feureau")
    else:
        # Take the username from arguments
        user_input = sys.argv[1]
        
        # Clean the input in case user typed '@feureau' instead of 'feureau'
        clean_username = user_input.replace("@", "").strip()
        
        get_user_links(clean_username)
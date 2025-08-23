# Enhanced media management with albums, tags, bulk upload, thumbnails, and share links
import streamlit as st
import os
from datetime import datetime, timedelta
import uuid
from utils.io import ensure_dir, read_json, write_json, safe_listdir
from utils.audit import log_audit_event
from utils.media_utils import create_thumbnail, get_video_metadata, get_image_metadata
from utils.sharelinks import generate_share_link, verify_share_link

PHOTO_DIR = "uploads/photos"
VIDEO_DIR = "uploads/videos"
THUMBNAILS_DIR = "uploads/thumbnails"
MEDIA_INDEX_FILE = "data/media_index.json"

def _load_media_index():
    """Load media index with albums, tags, and metadata"""
    try:
        return read_json(MEDIA_INDEX_FILE)
    except:
        return {"albums": [], "media": [], "tags": [], "shares": []}

def _save_media_index(data):
    """Save media index"""
    write_json(MEDIA_INDEX_FILE, data)

def _add_media_to_index(filename, file_type, album_id, tags, metadata, uploader):
    """Add media file to searchable index"""
    index = _load_media_index()
    
    media_entry = {
        "id": str(uuid.uuid4()),
        "filename": filename,
        "type": file_type,  # "photo" or "video"
        "album_id": album_id,
        "tags": tags,
        "metadata": metadata,
        "uploader": uploader,
        "uploaded_at": datetime.now().isoformat(),
        "views": 0
    }
    
    index["media"].append(media_entry)
    
    # Update tags list
    for tag in tags:
        if tag and tag not in index["tags"]:
            index["tags"].append(tag)
    
    _save_media_index(index)
    return media_entry["id"]

def _create_album(name, description, creator):
    """Create a new album"""
    index = _load_media_index()
    
    album = {
        "id": str(uuid.uuid4()),
        "name": name,
        "description": description,
        "creator": creator,
        "created_at": datetime.now().isoformat(),
        "media_count": 0
    }
    
    index["albums"].append(album)
    _save_media_index(index)
    return album["id"]

def _get_albums():
    """Get all albums"""
    index = _load_media_index()
    return index.get("albums", [])

def _get_album_media(album_id):
    """Get all media in an album"""
    index = _load_media_index()
    return [m for m in index.get("media", []) if m.get("album_id") == album_id]

def _search_media(query=None, album_id=None, tags=None):
    """Search media by various criteria"""
    index = _load_media_index()
    media = index.get("media", [])
    
    if album_id:
        media = [m for m in media if m.get("album_id") == album_id]
    
    if tags:
        tag_set = set(tags)
        media = [m for m in media if tag_set.intersection(set(m.get("tags", [])))]
    
    if query:
        query = query.lower()
        media = [m for m in media if 
                 query in m.get("filename", "").lower() or
                 query in " ".join(m.get("tags", [])).lower()]
    
    return media

def main(user: dict):
    """Enhanced media management interface"""
    st.header("📸 Media Center (Enhanced)")
    st.markdown("---")

    # Initialize directories
    ensure_dir(PHOTO_DIR)
    ensure_dir(VIDEO_DIR)
    ensure_dir(THUMBNAILS_DIR)

    # Load media index
    index = _load_media_index()

    # Navigation tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload", "📚 Albums", "🔍 Browse & Search", "🔗 Share Links"])

    with tab1:
        st.subheader("📤 Upload Media")
        
        if user["role"].lower() == "teacher":
            # Album selection/creation
            albums = _get_albums()
            album_options = ["Create New Album"] + [f"{a['name']} ({a.get('media_count', 0)} files)" for a in albums]
            
            album_choice = st.selectbox("📚 Select Album:", album_options)
            
            album_id = None
            if album_choice == "Create New Album":
                with st.form("new_album_form"):
                    new_album_name = st.text_input("📚 Album Name:", placeholder="e.g., Tech Fest 2025")
                    new_album_desc = st.text_area("📝 Description:", placeholder="Optional description of the album")
                    
                    if st.form_submit_button("Create Album"):
                        if new_album_name:
                            album_id = _create_album(new_album_name, new_album_desc, user["email"])
                            st.success(f"✅ Album '{new_album_name}' created!")
                            log_audit_event(user["email"], "CREATE", "ALBUM", album_id, {"name": new_album_name})
                            st.rerun()
                        else:
                            st.error("Please enter an album name.")
            else:
                # Find selected album ID
                selected_album_name = album_choice.split(" (")[0]
                album_id = next((a["id"] for a in albums if a["name"] == selected_album_name), None)
            
            if album_id:
                st.success(f"📚 Selected Album: {album_choice}")
                
                # Bulk upload interface
                st.markdown("### 📁 Bulk Upload")
                uploaded_files = st.file_uploader(
                    "🎯 Choose Photos or Videos:",
                    type=["jpg", "jpeg", "png", "mp4"],
                    accept_multiple_files=True,
                    help="Select multiple files to upload at once"
                )
                
                if uploaded_files:
                    st.info(f"📁 Selected {len(uploaded_files)} files")
                    
                    # Metadata form for all files
                    with st.form("bulk_upload_form"):
                        event_name = st.text_input("🎉 Event/Occasion:", placeholder="e.g., Annual Day, Workshop, etc.")
                        event_date = st.date_input("📅 Event Date:", value=datetime.now().date())
                        organizers = st.text_input("👥 Organizers/Faculty:", placeholder="e.g., Prof. Smith, CS Department")
                        
                        # Tags
                        common_tags = st.text_input(
                            "🏷️ Tags (comma-separated):",
                            placeholder="e.g., workshop, students, presentation, cs-dept",
                            help="Add tags to help organize and search your media"
                        )
                        
                        upload_submitted = st.form_submit_button("📤 Upload All Files", type="primary")
                        
                        if upload_submitted:
                            # Process tags
                            tags = [tag.strip().lower() for tag in common_tags.split(",") if tag.strip()]
                            if event_name:
                                tags.append(event_name.lower())
                            
                            # Upload progress
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            uploaded_count = 0
                            for i, uploaded_file in enumerate(uploaded_files):
                                try:
                                    status_text.text(f"Uploading {uploaded_file.name}...")
                                    
                                    # Determine file type
                                    name = uploaded_file.name
                                    is_image = name.lower().endswith((".jpg", ".jpeg", ".png"))
                                    is_video = name.lower().endswith(".mp4")
                                    
                                    if is_image:
                                        save_dir = PHOTO_DIR
                                        file_type = "photo"
                                    elif is_video:
                                        save_dir = VIDEO_DIR
                                        file_type = "video"
                                    else:
                                        st.error(f"❌ Unsupported file type: {name}")
                                        continue
                                    
                                    # Handle duplicate names
                                    base, ext = os.path.splitext(name)
                                    save_path = os.path.join(save_dir, name)
                                    counter = 1
                                    while os.path.exists(save_path):
                                        save_path = os.path.join(save_dir, f"{base}({counter}){ext}")
                                        counter += 1
                                    
                                    final_name = os.path.basename(save_path)
                                    
                                    # Save file
                                    with open(save_path, "wb") as f:
                                        f.write(uploaded_file.getbuffer())
                                    
                                    # Generate thumbnail for images
                                    thumbnail_path = None
                                    if is_image:
                                        thumbnail_path = create_thumbnail(save_path, final_name)
                                    
                                    # Get metadata
                                    metadata = {
                                        "event_name": event_name,
                                        "event_date": event_date.isoformat(),
                                        "organizers": organizers,
                                        "file_size_mb": round(len(uploaded_file.getbuffer()) / (1024*1024), 2)
                                    }
                                    
                                    if is_image:
                                        metadata.update(get_image_metadata(save_path))
                                        if thumbnail_path:
                                            metadata["thumbnail"] = os.path.basename(thumbnail_path)
                                    elif is_video:
                                        metadata.update(get_video_metadata(save_path))
                                    
                                    # Add to index
                                    media_id = _add_media_to_index(final_name, file_type, album_id, tags, metadata, user["email"])
                                    
                                    # Log upload
                                    log_audit_event(
                                        user["email"],
                                        "UPLOAD",
                                        "MEDIA",
                                        media_id,
                                        {"filename": final_name, "album_id": album_id, "type": file_type}
                                    )
                                    
                                    uploaded_count += 1
                                    progress_bar.progress((i + 1) / len(uploaded_files))
                                    
                                except Exception as e:
                                    st.error(f"❌ Failed to upload {uploaded_file.name}: {e}")
                            
                            status_text.empty()
                            progress_bar.empty()
                            
                            if uploaded_count > 0:
                                st.success(f"✅ Successfully uploaded {uploaded_count}/{len(uploaded_files)} files!")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error("❌ No files were uploaded successfully.")
        else:
            st.info("👁️ **Student Access:** Upload is restricted to teachers only")

    with tab2:
        st.subheader("📚 Albums")
        
        albums = _get_albums()
        if albums:
            # Album grid
            cols = st.columns(2)
            for i, album in enumerate(albums):
                with cols[i % 2]:
                    album_media = _get_album_media(album["id"])
                    media_count = len(album_media)
                    
                    with st.container():
                        st.markdown(f"### 📚 {album['name']}")
                        st.write(f"📁 **{media_count}** files")
                        if album.get("description"):
                            st.write(f"📝 {album['description']}")
                        st.caption(f"👤 Created by {album.get('creator', 'Unknown')} on {album.get('created_at', 'Unknown date')[:10]}")
                        
                        if st.button(f"👁️ View Album", key=f"view_{album['id']}"):
                            st.session_state.selected_album = album["id"]
                            st.session_state.album_name = album["name"]
                        
                        if user["role"].lower() == "teacher":
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button(f"🔗 Share", key=f"share_{album['id']}"):
                                    st.session_state.share_album = album["id"]
                            with col2:
                                if st.button(f"🗑️ Delete", key=f"delete_{album['id']}"):
                                    st.session_state.delete_album = album["id"]
                    st.markdown("---")
        else:
            st.info("📭 No albums created yet. Use the Upload tab to create your first album.")

    with tab3:
        st.subheader("🔍 Browse & Search Media")
        
        # Search interface
        col1, col2 = st.columns(2)
        with col1:
            search_query = st.text_input("🔍 Search:", placeholder="Search by filename or tags...")
        with col2:
            available_tags = index.get("tags", [])
            selected_tags = st.multiselect("🏷️ Filter by Tags:", available_tags)
        
        # Album filter
        albums = _get_albums()
        if albums:
            album_filter_options = ["All Albums"] + [a["name"] for a in albums]
            selected_album_name = st.selectbox("📚 Filter by Album:", album_filter_options)
            
            if selected_album_name != "All Albums":
                filter_album_id = next((a["id"] for a in albums if a["name"] == selected_album_name), None)
            else:
                filter_album_id = None
        else:
            filter_album_id = None
        
        # Perform search
        search_results = _search_media(search_query, filter_album_id, selected_tags)
        
        if search_results:
            st.write(f"📊 Found {len(search_results)} media files")
            
            # Display results
            for media in search_results[:20]:  # Limit to 20 results
                with st.expander(f"📁 {media['filename']} ({media['type']})", expanded=False):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        # Display media
                        if media["type"] == "photo":
                            file_path = os.path.join(PHOTO_DIR, media["filename"])
                            
                            # Show thumbnail if available
                            thumbnail_name = media.get("metadata", {}).get("thumbnail")
                            if thumbnail_name:
                                thumbnail_path = os.path.join(THUMBNAILS_DIR, thumbnail_name)
                                if os.path.exists(thumbnail_path):
                                    st.image(thumbnail_path, caption=media["filename"], width=200)
                            elif os.path.exists(file_path):
                                st.image(file_path, caption=media["filename"], width=200)
                        
                        elif media["type"] == "video":
                            file_path = os.path.join(VIDEO_DIR, media["filename"])
                            if os.path.exists(file_path):
                                with open(file_path, "rb") as video_file:
                                    video_bytes = video_file.read()
                                st.video(video_bytes)
                    
                    with col2:
                        st.write("**📋 Details:**")
                        st.write(f"📅 Uploaded: {media.get('uploaded_at', 'Unknown')[:10]}")
                        st.write(f"👤 By: {media.get('uploader', 'Unknown')}")
                        
                        if media.get("tags"):
                            st.write("🏷️ Tags:")
                            for tag in media["tags"]:
                                st.code(tag)
                        
                        metadata = media.get("metadata", {})
                        if metadata.get("event_name"):
                            st.write(f"🎉 Event: {metadata['event_name']}")
                        if metadata.get("file_size_mb"):
                            st.write(f"📊 Size: {metadata['file_size_mb']} MB")
                        
                        # Actions for teachers
                        if user["role"].lower() == "teacher":
                            if st.button(f"🔗 Share", key=f"share_media_{media['id']}"):
                                st.session_state.share_media = media["id"]
        else:
            st.info("🔍 No media found matching your search criteria.")

    with tab4:
        st.subheader("🔗 Share Links")
        
        if user["role"].lower() == "teacher":
            st.info("Generate time-limited share links for albums or individual media files")
            
            # Show existing share links
            shares = index.get("shares", [])
            active_shares = [s for s in shares if not verify_share_link(s["token"]) is None]
            
            if active_shares:
                st.write("**📋 Active Share Links:**")
                for share in active_shares:
                    expiry_dt = datetime.fromtimestamp(share["expiry_timestamp"])
                    time_left = expiry_dt - datetime.now()
                    
                    if time_left.total_seconds() > 0:
                        hours_left = int(time_left.total_seconds() / 3600)
                        st.success(f"🔗 {share['name']} - Expires in {hours_left}h")
                        st.code(f"Share Token: {share['token'][:20]}...", language=None)
                    else:
                        st.error(f"❌ {share['name']} - Expired")
        else:
            st.info("👁️ **Student Access:** Share link generation is restricted to teachers only")

    # Handle session state actions
    if "share_album" in st.session_state:
        album_id = st.session_state.share_album
        album = next((a for a in albums if a["id"] == album_id), None)
        if album:
            st.success(f"🔗 Generating share link for album: {album['name']}")
            # Implementation for album sharing would go here
        del st.session_state.share_album

    if "delete_album" in st.session_state:
        album_id = st.session_state.delete_album
        st.warning("🗑️ Album deletion feature coming soon...")
        del st.session_state.delete_album

    # Usage statistics
    with st.expander("📊 **Media Statistics**", expanded=False):
        total_media = len(index.get("media", []))
        total_albums = len(albums)
        total_tags = len(index.get("tags", []))
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📁 Total Files", total_media)
        with col2:
            st.metric("📚 Albums", total_albums)
        with col3:
            st.metric("🏷️ Tags", total_tags)

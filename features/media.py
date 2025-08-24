# Enhanced media management with approval workflow, bulk actions, and optimized images
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
        return {"albums": [], "media": [], "tags": [], "shares": [], "pending_approval": []}

def _save_media_index(data):
    """Save media index"""
    write_json(MEDIA_INDEX_FILE, data)

def _add_media_to_index(filename, file_type, album_id, tags, metadata, uploader, approval_status="approved"):
    """Add media file to searchable index with approval workflow"""
    index = _load_media_index()
    
    media_entry = {
        "id": str(uuid.uuid4()),
        "filename": filename,
        "type": file_type,
        "album_id": album_id,
        "tags": tags,
        "metadata": metadata,
        "uploader": uploader,
        "uploaded_at": datetime.now().isoformat(),
        "approval_status": approval_status,  # "pending", "approved", "rejected"
        "approved_by": None,
        "approved_at": None,
        "views": 0
    }
    
    if approval_status == "pending":
        index["pending_approval"].append(media_entry)
    else:
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
        "media_count": 0,
        "visibility": "public"  # "public", "private", "department_only"
    }
    
    index["albums"].append(album)
    _save_media_index(index)
    return album["id"]

def _get_albums():
    """Get all albums"""
    index = _load_media_index()
    return index.get("albums", [])

def _get_album_media(album_id, include_pending=False):
    """Get all media in an album"""
    index = _load_media_index()
    media = [m for m in index.get("media", []) if m.get("album_id") == album_id]
    
    if include_pending:
        pending = [m for m in index.get("pending_approval", []) if m.get("album_id") == album_id]
        media.extend(pending)
    
    return media

def _search_media(query=None, album_id=None, tags=None, file_type=None, date_from=None, date_to=None):
    """Advanced search with multiple filters"""
    index = _load_media_index()
    media = index.get("media", [])
    
    # Filter by album
    if album_id:
        media = [m for m in media if m.get("album_id") == album_id]
    
    # Filter by tags
    if tags:
        tag_set = set(tags)
        media = [m for m in media if tag_set.intersection(set(m.get("tags", [])))]
    
    # Filter by file type
    if file_type and file_type != "All":
        media = [m for m in media if m.get("type") == file_type.lower()]
    
    # Filter by date range
    if date_from or date_to:
        for m in media[:]:
            upload_date = datetime.fromisoformat(m.get("uploaded_at", "")).date()
            if date_from and upload_date < date_from:
                media.remove(m)
                continue
            if date_to and upload_date > date_to:
                media.remove(m)
    
    # Text search
    if query:
        query = query.lower()
        media = [m for m in media if 
                 query in m.get("filename", "").lower() or
                 query in " ".join(m.get("tags", [])).lower() or
                 query in m.get("metadata", {}).get("event_name", "").lower()]
    
    return media

def _delete_album(album_id, user_email):
    """Delete an album and all its media"""
    index = _load_media_index()
    
    # Remove album
    index["albums"] = [a for a in index["albums"] if a["id"] != album_id]
    
    # Remove media files and entries
    album_media = [m for m in index["media"] if m.get("album_id") == album_id]
    
    for media in album_media:
        # Delete physical files
        if media["type"] == "photo":
            file_path = os.path.join(PHOTO_DIR, media["filename"])
        else:
            file_path = os.path.join(VIDEO_DIR, media["filename"])
        
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Delete thumbnail if exists
            thumbnail_name = media.get("metadata", {}).get("thumbnail")
            if thumbnail_name:
                thumb_path = os.path.join(THUMBNAILS_DIR, thumbnail_name)
                if os.path.exists(thumb_path):
                    os.remove(thumb_path)
        except Exception as e:
            st.error(f"Error deleting file {media['filename']}: {e}")
    
    # Remove media entries
    index["media"] = [m for m in index["media"] if m.get("album_id") != album_id]
    
    _save_media_index(index)
    
    # Log deletion
    log_audit_event(user_email, "DELETE", "ALBUM", album_id, {"album_media_count": len(album_media)})

def main(user: dict):
    """Enhanced media management interface"""
    st.header("📸 Enhanced Media Center")
    st.markdown("---")

    # Initialize directories
    ensure_dir(PHOTO_DIR)
    ensure_dir(VIDEO_DIR)
    ensure_dir(THUMBNAILS_DIR)

    # Load media index
    index = _load_media_index()

    # Enhanced navigation tabs
    if user["role"].lower() == "teacher":
        tabs = st.tabs(["📤 Upload", "📚 Albums", "🔍 Advanced Search", "🔗 Share Links", "⚙️ Admin Panel"])
        tab1, tab2, tab3, tab4, tab5 = tabs
    else:
        tabs = st.tabs(["📚 Albums", "🔍 Advanced Search"])
        tab2, tab3 = tabs
        tab1, tab4, tab5 = None, None, None

    if tab1:  # Upload tab (Teachers only)
        with tab1:
            show_upload_interface(user, index)

    with tab2:  # Albums tab
        show_albums_interface(user, index)

    with tab3:  # Advanced Search tab
        show_advanced_search_interface(user, index)

    if tab4:  # Share Links tab (Teachers only)
        with tab4:
            show_share_links_interface(user, index)

    if tab5:  # Admin Panel tab (Teachers only)
        with tab5:
            show_admin_panel_interface(user, index)

def show_upload_interface(user, index):
    """Enhanced upload interface with bulk operations"""
    st.subheader("📤 Enhanced Upload Center")
    
    # Album selection/creation
    albums = _get_albums()
    album_options = ["Create New Album"] + [f"{a['name']} ({len(_get_album_media(a['id']))} files)" for a in albums]
    
    album_choice = st.selectbox("📚 Select Album:", album_options)
    
    album_id = None
    if album_choice == "Create New Album":
        with st.form("new_album_form"):
            new_album_name = st.text_input("📚 Album Name:", placeholder="e.g., Tech Fest 2025")
            new_album_desc = st.text_area("📝 Description:", placeholder="Optional description of the album")
            album_visibility = st.selectbox("👁️ Visibility:", ["Public", "Department Only", "Private"])
            
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
        
        # Enhanced bulk upload interface
        st.markdown("### 📁 Bulk Upload with Enhanced Metadata")
        uploaded_files = st.file_uploader(
            "🎯 Choose Photos or Videos:",
            type=["jpg", "jpeg", "png", "mp4"],
            accept_multiple_files=True,
            help="Select multiple files (max 50MB each)"
        )
        
        if uploaded_files:
            st.info(f"📁 Selected {len(uploaded_files)} files")
            
            # Enhanced metadata form
            with st.form("bulk_upload_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    event_name = st.text_input("🎉 Event/Occasion:", placeholder="e.g., Annual Day, Workshop")
                    event_date = st.date_input("📅 Event Date:", value=datetime.now().date())
                    organizers = st.text_input("👥 Organizers/Faculty:", placeholder="e.g., Prof. Smith, CS Department")
                
                with col2:
                    event_location = st.text_input("📍 Location:", placeholder="e.g., Auditorium, Lab 101")
                    department = st.selectbox("🏢 Department:", ["Computer Science", "Electronics", "Mechanical", "Other"])
                    event_type = st.selectbox("🎭 Event Type:", ["Academic", "Cultural", "Sports", "Workshop", "Seminar", "Other"])
                
                # Enhanced tags
                common_tags = st.text_input(
                    "🏷️ Tags (comma-separated):",
                    placeholder="e.g., workshop, students, presentation, cs-dept",
                    help="Add tags to help organize and search your media"
                )
                
                # Approval settings
                requires_approval = st.checkbox(
                    "⚖️ Requires Approval",
                    value=False,
                    help="Check if media should be reviewed before being visible to all users"
                )
                
                upload_submitted = st.form_submit_button("📤 Upload All Files", type="primary")
                
                if upload_submitted:
                    upload_files_with_metadata(
                        uploaded_files, album_id, user, event_name, event_date, 
                        organizers, event_location, department, event_type, 
                        common_tags, requires_approval
                    )

def upload_files_with_metadata(uploaded_files, album_id, user, event_name, event_date, 
                               organizers, event_location, department, event_type, 
                               common_tags, requires_approval):
    """Enhanced file upload with comprehensive metadata"""
    # Process tags
    tags = [tag.strip().lower() for tag in common_tags.split(",") if tag.strip()]
    if event_name:
        tags.append(event_name.lower())
    tags.extend([department.lower(), event_type.lower()])
    
    # Upload progress
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    uploaded_count = 0
    approval_status = "pending" if requires_approval else "approved"
    
    for i, uploaded_file in enumerate(uploaded_files):
        try:
            status_text.text(f"Processing {uploaded_file.name}...")
            
            # File size check
            file_size_mb = len(uploaded_file.getbuffer()) / (1024*1024)
            if file_size_mb > 50:
                st.error(f"❌ File {uploaded_file.name} is too large ({file_size_mb:.1f}MB). Maximum size is 50MB.")
                continue
            
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
            
            # Generate optimized thumbnail for images
            thumbnail_path = None
            if is_image:
                thumbnail_path = create_thumbnail(save_path, final_name)
            
            # Enhanced metadata
            metadata = {
                "event_name": event_name,
                "event_date": event_date.isoformat(),
                "organizers": organizers,
                "event_location": event_location,
                "department": department,
                "event_type": event_type,
                "file_size_mb": round(file_size_mb, 2),
                "original_filename": name
            }
            
            if is_image:
                img_meta = get_image_metadata(save_path)
                metadata.update(img_meta)
                if thumbnail_path:
                    metadata["thumbnail"] = os.path.basename(thumbnail_path)
            elif is_video:
                vid_meta = get_video_metadata(save_path)
                metadata.update(vid_meta)
            
            # Add to index
            media_id = _add_media_to_index(
                final_name, file_type, album_id, tags, metadata, 
                user["email"], approval_status
            )
            
            # Log upload
            log_audit_event(
                user["email"],
                "UPLOAD",
                "MEDIA",
                media_id,
                {
                    "filename": final_name, 
                    "album_id": album_id, 
                    "type": file_type,
                    "approval_status": approval_status
                }
            )
            
            uploaded_count += 1
            progress_bar.progress((i + 1) / len(uploaded_files))
            
        except Exception as e:
            st.error(f"❌ Failed to upload {uploaded_file.name}: {e}")
    
    status_text.empty()
    progress_bar.empty()
    
    if uploaded_count > 0:
        if requires_approval:
            st.success(f"✅ Successfully uploaded {uploaded_count}/{len(uploaded_files)} files!")
            st.info("⚖️ Files are pending approval before being visible to all users.")
        else:
            st.success(f"✅ Successfully uploaded {uploaded_count}/{len(uploaded_files)} files!")
        st.balloons()
        st.rerun()
    else:
        st.error("❌ No files were uploaded successfully.")

def show_albums_interface(user, index):
    """Enhanced albums interface with management options"""
    st.subheader("📚 Enhanced Albums Management")
    
    albums = _get_albums()
    
    if albums:
        # Albums display with enhanced options
        for album in albums:
            album_media = _get_album_media(album["id"])
            media_count = len(album_media)
            
            with st.expander(f"📚 {album['name']} ({media_count} files)", expanded=False):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    if album.get("description"):
                        st.write(f"📝 **Description:** {album['description']}")
                    
                    st.write(f"👤 **Created by:** {album.get('creator', 'Unknown')}")
                    st.write(f"📅 **Created:** {album.get('created_at', 'Unknown')[:10]}")
                    st.write(f"👁️ **Visibility:** {album.get('visibility', 'Public')}")
                    
                    # Display media thumbnails (optimized size)
                    if media_count > 0:
                        st.write("**🖼️ Media Preview:**")
                        cols = st.columns(min(4, media_count))
                        
                        for i, media in enumerate(album_media[:4]):
                            with cols[i]:
                                if media["type"] == "photo":
                                    # Use thumbnail if available
                                    thumbnail_name = media.get("metadata", {}).get("thumbnail")
                                    if thumbnail_name:
                                        thumbnail_path = os.path.join(THUMBNAILS_DIR, thumbnail_name)
                                        if os.path.exists(thumbnail_path):
                                            st.image(thumbnail_path, use_container_width=True)
                                        else:
                                            file_path = os.path.join(PHOTO_DIR, media["filename"])
                                            if os.path.exists(file_path):
                                                st.image(file_path, use_container_width=True)
                                    else:
                                        file_path = os.path.join(PHOTO_DIR, media["filename"])
                                        if os.path.exists(file_path):
                                            st.image(file_path, use_container_width=True)
                                
                                elif media["type"] == "video":
                                    st.write(f"🎥 {media['filename']}")
                        
                        if media_count > 4:
                            st.caption(f"... and {media_count - 4} more files")
                
                with col2:
                    st.write("**⚡ Actions:**")
                    
                    if st.button(f"👁️ View", key=f"view_{album['id']}"):
                        st.session_state.view_album = album["id"]
                        st.session_state.album_name = album["name"]
                    
                    if user["role"].lower() == "teacher":
                        if st.button(f"📤 Upload", key=f"upload_{album['id']}"):
                            st.session_state.selected_album = album["id"]
                        
                        if st.button(f"🔗 Share", key=f"share_{album['id']}"):
                            st.session_state.share_album = album["id"]
                        
                        if st.button(f"🗑️ Delete", key=f"delete_{album['id']}", type="secondary"):
                            if st.session_state.get(f"confirm_delete_{album['id']}", False):
                                _delete_album(album["id"], user["email"])
                                st.success(f"Album '{album['name']}' deleted successfully!")
                                st.rerun()
                            else:
                                st.session_state[f"confirm_delete_{album['id']}"] = True
                                st.warning("⚠️ Click delete again to confirm")
    else:
        st.info("📭 No albums created yet.")
        if user["role"].lower() == "teacher":
            st.info("Use the Upload tab to create your first album.")

def show_advanced_search_interface(user, index):
    """Advanced search interface with multiple filters"""
    st.subheader("🔍 Advanced Media Search")
    
    # Search filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        search_query = st.text_input("🔍 Search:", placeholder="Keywords, event names, etc.")
        file_type = st.selectbox("📁 File Type:", ["All", "Photo", "Video"])
    
    with col2:
        available_tags = index.get("tags", [])
        selected_tags = st.multiselect("🏷️ Tags:", available_tags)
        
        albums = _get_albums()
        if albums:
            album_options = ["All Albums"] + [a["name"] for a in albums]
            selected_album = st.selectbox("📚 Album:", album_options)
        else:
            selected_album = "All Albums"
    
    with col3:
        col3a, col3b = st.columns(2)
        with col3a:
            date_from = st.date_input("📅 From:", value=None)
        with col3b:
            date_to = st.date_input("📅 To:", value=None)
    
    # Search button and results
    if st.button("🔍 Search", type="primary"):
        # Get album ID if specific album selected
        if selected_album != "All Albums":
            filter_album_id = next((a["id"] for a in albums if a["name"] == selected_album), None)
        else:
            filter_album_id = None
        
        # Perform search
        search_results = _search_media(
            query=search_query,
            album_id=filter_album_id,
            tags=selected_tags,
            file_type=file_type,
            date_from=date_from,
            date_to=date_to
        )
        
        if search_results:
            st.success(f"📊 Found {len(search_results)} results")
            
            # Bulk actions for teachers
            if user["role"].lower() == "teacher" and len(search_results) > 1:
                show_bulk_actions_interface(user, search_results)
            
            # Display results with optimized images
            display_search_results(search_results, user)
        else:
            st.info("🔍 No media found matching your search criteria.")

def show_bulk_actions_interface(user, search_results):
    """Bulk actions interface for teachers"""
    st.markdown("### ⚡ Bulk Actions")
    
    with st.form("bulk_actions_form"):
        # Select items for bulk action
        selected_items = st.multiselect(
            "Select items for bulk action:",
            [f"{r['filename']} ({r['type']})" for r in search_results],
            help="Choose multiple items to perform bulk operations"
        )
        
        if selected_items:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                bulk_action = st.selectbox(
                    "Choose action:",
                    ["Move to Album", "Add Tags", "Delete Selected"]
                )
            
            with col2:
                if bulk_action == "Move to Album":
                    albums = _get_albums()
                    if albums:
                        target_album = st.selectbox("Target Album:", [a["name"] for a in albums])
                    else:
                        st.warning("No albums available")
                        target_album = None
                elif bulk_action == "Add Tags":
                    new_tags = st.text_input("Tags to add:", placeholder="tag1, tag2, tag3")
                else:
                    st.warning("⚠️ This will permanently delete selected files")
            
            if st.form_submit_button("Execute Bulk Action", type="secondary"):
                execute_bulk_action(user, search_results, selected_items, bulk_action, locals())

def execute_bulk_action(user, search_results, selected_items, action, action_params):
    """Execute bulk actions on selected media"""
    selected_media = [
        r for r in search_results 
        if f"{r['filename']} ({r['type']})" in selected_items
    ]
    
    if action == "Delete Selected":
        # Bulk delete implementation
        for media in selected_media:
            # Delete physical file
            if media["type"] == "photo":
                file_path = os.path.join(PHOTO_DIR, media["filename"])
            else:
                file_path = os.path.join(VIDEO_DIR, media["filename"])
            
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                
                # Delete thumbnail
                thumbnail_name = media.get("metadata", {}).get("thumbnail")
                if thumbnail_name:
                    thumb_path = os.path.join(THUMBNAILS_DIR, thumbnail_name)
                    if os.path.exists(thumb_path):
                        os.remove(thumb_path)
                
                # Remove from index
                index = _load_media_index()
                index["media"] = [m for m in index["media"] if m["id"] != media["id"]]
                _save_media_index(index)
                
                # Log deletion
                log_audit_event(user["email"], "DELETE", "MEDIA", media["id"], {"bulk_action": True})
                
            except Exception as e:
                st.error(f"Error deleting {media['filename']}: {e}")
        
        st.success(f"✅ Deleted {len(selected_media)} files")
        st.rerun()
    
    elif action == "Add Tags":
        new_tags = action_params.get("new_tags", "").split(",")
        new_tags = [tag.strip().lower() for tag in new_tags if tag.strip()]
        
        if new_tags:
            index = _load_media_index()
            
            for media in selected_media:
                # Find and update media entry
                for m in index["media"]:
                    if m["id"] == media["id"]:
                        existing_tags = set(m.get("tags", []))
                        existing_tags.update(new_tags)
                        m["tags"] = list(existing_tags)
                        break
            
            # Update global tags list
            all_tags = set(index.get("tags", []))
            all_tags.update(new_tags)
            index["tags"] = list(all_tags)
            
            _save_media_index(index)
            st.success(f"✅ Added tags to {len(selected_media)} files")
            st.rerun()

def display_search_results(search_results, user):
    """Display search results with optimized image sizes"""
    # Results per page
    items_per_page = 12
    total_pages = (len(search_results) + items_per_page - 1) // items_per_page
    
    if total_pages > 1:
        page = st.selectbox("📄 Page:", range(1, total_pages + 1), key="search_page")
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_results = search_results[start_idx:end_idx]
    else:
        page_results = search_results
    
    # Display in grid (3 columns for better viewing)
    cols = st.columns(3)
    
    for i, media in enumerate(page_results):
        with cols[i % 3]:
            # Display media with optimized size
            if media["type"] == "photo":
                # Use thumbnail for better performance
                thumbnail_name = media.get("metadata", {}).get("thumbnail")
                if thumbnail_name:
                    thumbnail_path = os.path.join(THUMBNAILS_DIR, thumbnail_name)
                    if os.path.exists(thumbnail_path):
                        st.image(thumbnail_path, caption=media["filename"], use_container_width=True)
                    else:
                        file_path = os.path.join(PHOTO_DIR, media["filename"])
                        if os.path.exists(file_path):
                            st.image(file_path, caption=media["filename"], width=200)  # Fixed smaller width
                else:
                    file_path = os.path.join(PHOTO_DIR, media["filename"])
                    if os.path.exists(file_path):
                        st.image(file_path, caption=media["filename"], width=200)  # Fixed smaller width
            
            elif media["type"] == "video":
                st.write(f"🎥 **{media['filename']}**")
                # Show video metadata instead of full video
                metadata = media.get("metadata", {})
                if metadata.get("duration"):
                    st.caption(f"⏱️ Duration: {metadata['duration']}")
                if metadata.get("size_mb"):
                    st.caption(f"📊 Size: {metadata['size_mb']} MB")
            
            # Show metadata
            st.caption(f"📅 {media.get('uploaded_at', '')[:10]}")
            st.caption(f"👤 {media.get('uploader', 'Unknown')}")
            
            # Show tags
            if media.get("tags"):
                tag_str = " ".join([f"#{tag}" for tag in media["tags"][:3]])
                st.caption(f"🏷️ {tag_str}")
            
            # Action buttons for teachers
            if user["role"].lower() == "teacher":
                if st.button(f"🗑️", key=f"del_{media['id']}", help="Delete this file"):
                    delete_single_media(media, user["email"])
                    st.rerun()

def delete_single_media(media, user_email):
    """Delete a single media file"""
    try:
        # Delete physical file
        if media["type"] == "photo":
            file_path = os.path.join(PHOTO_DIR, media["filename"])
        else:
            file_path = os.path.join(VIDEO_DIR, media["filename"])
        
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Delete thumbnail
        thumbnail_name = media.get("metadata", {}).get("thumbnail")
        if thumbnail_name:
            thumb_path = os.path.join(THUMBNAILS_DIR, thumbnail_name)
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
        
        # Remove from index
        index = _load_media_index()
        index["media"] = [m for m in index["media"] if m["id"] != media["id"]]
        _save_media_index(index)
        
        # Log deletion
        log_audit_event(user_email, "DELETE", "MEDIA", media["id"], {"single_delete": True})
        
        st.success(f"✅ Deleted {media['filename']}")
        
    except Exception as e:
        st.error(f"❌ Error deleting {media['filename']}: {e}")

def show_share_links_interface(user, index):
    """Enhanced share links interface"""
    st.subheader("🔗 Share Links Management")
    st.info("Generate time-limited share links for albums or individual media files")
    
    # Implementation would go here for share links
    st.info("🚧 Share links feature coming soon with enhanced security and analytics")

def show_admin_panel_interface(user, index):
    """Admin panel for media approval and management"""
    st.subheader("⚙️ Media Administration Panel")
    
    # Pending approvals
    pending_media = index.get("pending_approval", [])
    
    if pending_media:
        st.markdown(f"#### ⚖️ Pending Approvals ({len(pending_media)})")
        
        for media in pending_media:
            with st.expander(f"📋 {media['filename']} - {media.get('uploader', 'Unknown')}", expanded=False):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # Show media preview
                    if media["type"] == "photo":
                        file_path = os.path.join(PHOTO_DIR, media["filename"])
                        if os.path.exists(file_path):
                            st.image(file_path, width=300)
                    
                    # Show metadata
                    metadata = media.get("metadata", {})
                    st.write(f"**📅 Event:** {metadata.get('event_name', 'N/A')}")
                    st.write(f"**📍 Location:** {metadata.get('event_location', 'N/A')}")
                    st.write(f"**👥 Organizers:** {metadata.get('organizers', 'N/A')}")
                    st.write(f"**🏷️ Tags:** {', '.join(media.get('tags', []))}")
                
                with col2:
                    st.write("**⚖️ Review Actions:**")
                    
                    if st.button("✅ Approve", key=f"approve_{media['id']}"):
                        approve_media(media, user["email"])
                        st.success("Media approved!")
                        st.rerun()
                    
                    if st.button("❌ Reject", key=f"reject_{media['id']}", type="secondary"):
                        reject_media(media, user["email"])
                        st.success("Media rejected!")
                        st.rerun()
    else:
        st.info("✅ No media pending approval")
    
    # Statistics
    st.markdown("---")
    st.markdown("#### 📊 Media Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_media = len(index.get("media", []))
        st.metric("📁 Total Media", total_media)
    
    with col2:
        total_albums = len(index.get("albums", []))
        st.metric("📚 Albums", total_albums)
    
    with col3:
        pending_count = len(pending_media)
        st.metric("⏳ Pending", pending_count)
    
    with col4:
        total_tags = len(index.get("tags", []))
        st.metric("🏷️ Tags", total_tags)

def approve_media(media, approver_email):
    """Approve pending media"""
    index = _load_media_index()
    
    # Remove from pending
    index["pending_approval"] = [m for m in index["pending_approval"] if m["id"] != media["id"]]
    
    # Add to approved media
    media["approval_status"] = "approved"
    media["approved_by"] = approver_email
    media["approved_at"] = datetime.now().isoformat()
    
    index["media"].append(media)
    
    # Update tags
    for tag in media.get("tags", []):
        if tag not in index.get("tags", []):
            index["tags"].append(tag)
    
    _save_media_index(index)
    
    # Log approval
    log_audit_event(approver_email, "APPROVE", "MEDIA", media["id"], {"uploader": media.get("uploader")})

def reject_media(media, rejector_email):
    """Reject pending media"""
    index = _load_media_index()
    
    # Remove from pending
    index["pending_approval"] = [m for m in index["pending_approval"] if m["id"] != media["id"]]
    
    # Delete physical file
    if media["type"] == "photo":
        file_path = os.path.join(PHOTO_DIR, media["filename"])
    else:
        file_path = os.path.join(VIDEO_DIR, media["filename"])
    
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Delete thumbnail if exists
        thumbnail_name = media.get("metadata", {}).get("thumbnail")
        if thumbnail_name:
            thumb_path = os.path.join(THUMBNAILS_DIR, thumbnail_name)
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
    except Exception as e:
        st.error(f"Error deleting rejected file: {e}")
    
    _save_media_index(index)
    
    # Log rejection
    log_audit_event(rejector_email, "REJECT", "MEDIA", media["id"], {"uploader": media.get("uploader")})

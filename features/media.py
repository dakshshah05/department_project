# Enhanced media management with fixed view button, optimized images, and video playback
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
        "approval_status": approval_status,
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
        "visibility": "public"
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

def main(user: dict):
    """Enhanced media management interface with fixed functionality"""
    st.header("📸 Enhanced Media Center")
    st.markdown("---")

    # Initialize directories
    ensure_dir(PHOTO_DIR)
    ensure_dir(VIDEO_DIR)
    ensure_dir(THUMBNAILS_DIR)

    # Load media index
    index = _load_media_index()

    # Check if viewing a specific album
    if "selected_album" in st.session_state:
        show_album_viewer(st.session_state.selected_album, user)
        return

    # Enhanced navigation tabs
    if user["role"].lower() == "teacher":
        tabs = st.tabs(["📤 Upload", "📚 Albums", "🔍 Browse & Search"])
        tab1, tab2, tab3 = tabs
    else:
        tabs = st.tabs(["📚 Albums", "🔍 Browse & Search"])
        tab2, tab3 = tabs
        tab1 = None

    if tab1:  # Upload tab (Teachers only)
        with tab1:
            show_upload_interface(user, index)

    with tab2:  # Albums tab
        show_albums_interface(user, index)

    with tab3:  # Browse & Search tab
        show_browse_interface(user, index)

def show_upload_interface(user, index):
    """Enhanced upload interface"""
    st.subheader("📤 Upload Media")
    
    # Album selection/creation
    albums = _get_albums()
    album_options = ["Create New Album"] + [f"{a['name']} ({len(_get_album_media(a['id']))} files)" for a in albums]
    
    album_choice = st.selectbox("📚 Select Album:", album_options)
    
    album_id = None
    if album_choice == "Create New Album":
        with st.form("new_album_form"):
            new_album_name = st.text_input("📚 Album Name:", placeholder="e.g., Tech Fest 2025")
            new_album_desc = st.text_area("📝 Description:", placeholder="Optional description")
            
            if st.form_submit_button("Create Album"):
                if new_album_name:
                    album_id = _create_album(new_album_name, new_album_desc, user["email"])
                    st.success(f"✅ Album '{new_album_name}' created!")
                    log_audit_event(user["email"], "CREATE", "ALBUM", album_id, {"name": new_album_name})
                    st.rerun()
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
            help="Select multiple files (max 50MB each)"
        )
        
        if uploaded_files:
            st.info(f"📁 Selected {len(uploaded_files)} files")
            
            # Metadata form
            with st.form("bulk_upload_form"):
                event_name = st.text_input("🎉 Event/Occasion:", placeholder="e.g., Annual Day")
                event_date = st.date_input("📅 Event Date:", value=datetime.now().date())
                organizers = st.text_input("👥 Organizers:", placeholder="e.g., Prof. Smith")
                
                common_tags = st.text_input(
                    "🏷️ Tags (comma-separated):",
                    placeholder="e.g., workshop, students, presentation",
                    help="Add tags to help organize your media"
                )
                
                upload_submitted = st.form_submit_button("📤 Upload All Files", type="primary")
                
                if upload_submitted:
                    upload_files_with_metadata(
                        uploaded_files, album_id, user, event_name, event_date, 
                        organizers, common_tags
                    )

def upload_files_with_metadata(uploaded_files, album_id, user, event_name, event_date, organizers, common_tags):
    """Enhanced file upload with metadata"""
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
            status_text.text(f"Processing {uploaded_file.name}...")
            
            # File size check
            file_size_mb = len(uploaded_file.getbuffer()) / (1024*1024)
            if file_size_mb > 50:
                st.error(f"❌ File {uploaded_file.name} is too large ({file_size_mb:.1f}MB)")
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
            
            # Generate thumbnail for images
            thumbnail_path = None
            if is_image:
                thumbnail_path = create_thumbnail(save_path, final_name)
            
            # Metadata
            metadata = {
                "event_name": event_name,
                "event_date": event_date.isoformat(),
                "organizers": organizers,
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
                final_name, file_type, album_id, tags, metadata, user["email"]
            )
            
            # Log upload
            log_audit_event(user["email"], "UPLOAD", "MEDIA", media_id, {
                "filename": final_name, "album_id": album_id, "type": file_type
            })
            
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

def show_albums_interface(user, index):
    """Enhanced albums interface with working view button"""
    st.subheader("📚 Albums Management")
    
    albums = _get_albums()
    
    if albums:
        # Albums display
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
                    
                    # Display small media thumbnails (FIXED: Small size)
                    if media_count > 0:
                        st.write("**🖼️ Media Preview:**")
                        cols = st.columns(min(4, media_count))
                        
                        for i, media in enumerate(album_media[:4]):
                            with cols[i]:
                                if media["type"] == "photo":
                                    # Use thumbnail if available (FIXED: Thumbnail instead of full image)
                                    thumbnail_name = media.get("metadata", {}).get("thumbnail")
                                    if thumbnail_name:
                                        thumbnail_path = os.path.join(THUMBNAILS_DIR, thumbnail_name)
                                        if os.path.exists(thumbnail_path):
                                            st.image(thumbnail_path, width=100)  # FIXED: Small width
                                        else:
                                            file_path = os.path.join(PHOTO_DIR, media["filename"])
                                            if os.path.exists(file_path):
                                                st.image(file_path, width=100)  # FIXED: Small width
                                    else:
                                        file_path = os.path.join(PHOTO_DIR, media["filename"])
                                        if os.path.exists(file_path):
                                            st.image(file_path, width=100)  # FIXED: Small width
                                
                                elif media["type"] == "video":
                                    st.write(f"🎥 {media['filename'][:15]}...")
                        
                        if media_count > 4:
                            st.caption(f"... and {media_count - 4} more files")
                
                with col2:
                    st.write("**⚡ Actions:**")
                    
                    # FIXED: Working view button with session state and rerun
                    if st.button(f"👁️ View Full Album", key=f"view_{album['id']}"):
                        st.session_state.selected_album = album["id"]
                        st.session_state.album_name = album["name"]
                        st.rerun()  # FIXED: Added rerun to refresh page
                    
                    if user["role"].lower() == "teacher":
                        if st.button(f"🗑️ Delete", key=f"delete_{album['id']}", type="secondary"):
                            if st.session_state.get(f"confirm_delete_{album['id']}", False):
                                delete_album(album["id"], user["email"])
                                st.success(f"Album '{album['name']}' deleted!")
                                st.rerun()
                            else:
                                st.session_state[f"confirm_delete_{album['id']}"] = True
                                st.warning("⚠️ Click delete again to confirm")
    else:
        st.info("📭 No albums created yet.")

def show_album_viewer(album_id, user):
    """FIXED: Full album viewer with proper image sizes and video playback"""
    albums = _get_albums()
    album = next((a for a in albums if a["id"] == album_id), None)
    
    if not album:
        st.error("❌ Album not found")
        if st.button("🔙 Back to Albums"):
            del st.session_state.selected_album
            st.rerun()
        return
    
    # Header with back button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔙 Back to Albums"):
            del st.session_state.selected_album
            if "album_name" in st.session_state:
                del st.session_state.album_name
            st.rerun()
    
    with col2:
        st.header(f"📚 {album['name']}")
    
    st.markdown("---")
    
    # Get album media
    album_media = _get_album_media(album_id)
    
    if album_media:
        st.info(f"📊 **{len(album_media)} files** in this album")
        
        # Display media in grid (FIXED: Proper sizing and video playback)
        cols = st.columns(3)
        
        for i, media in enumerate(album_media):
            with cols[i % 3]:
                st.markdown(f"**📁 {media['filename']}**")
                
                if media["type"] == "photo":
                    # FIXED: Use thumbnail for preview, full image on click
                    thumbnail_name = media.get("metadata", {}).get("thumbnail")
                    if thumbnail_name:
                        thumbnail_path = os.path.join(THUMBNAILS_DIR, thumbnail_name)
                        if os.path.exists(thumbnail_path):
                            st.image(thumbnail_path, width=200)  # FIXED: Reasonable size
                        else:
                            file_path = os.path.join(PHOTO_DIR, media["filename"])
                            if os.path.exists(file_path):
                                st.image(file_path, width=200)  # FIXED: Reasonable size
                    else:
                        file_path = os.path.join(PHOTO_DIR, media["filename"])
                        if os.path.exists(file_path):
                            st.image(file_path, width=200)  # FIXED: Reasonable size
                    
                    # Option to view full size
                    if st.button(f"🔍 View Full Size", key=f"full_{media['id']}"):
                        file_path = os.path.join(PHOTO_DIR, media["filename"])
                        if os.path.exists(file_path):
                            st.image(file_path, caption=f"Full Size: {media['filename']}")
                
                elif media["type"] == "video":
                    # FIXED: Proper video playback
                    video_path = os.path.join(VIDEO_DIR, media["filename"])
                    
                    if os.path.exists(video_path):
                        try:
                            # FIXED: Open video file as bytes and use st.video
                            with open(video_path, "rb") as video_file:
                                video_bytes = video_file.read()
                            
                            st.video(video_bytes, format="video/mp4")  # FIXED: Proper video display
                            
                            # Show video metadata
                            metadata = media.get("metadata", {})
                            if metadata.get("size_mb"):
                                st.caption(f"📊 Size: {metadata['size_mb']} MB")
                            if metadata.get("duration"):
                                st.caption(f"⏱️ Duration: {metadata['duration']}")
                                
                        except Exception as e:
                            st.error(f"❌ Cannot play video: {e}")
                            st.info("💡 Try converting video to H.264 format for better compatibility")
                    else:
                        st.error(f"❌ Video file not found: {media['filename']}")
                
                # Show metadata
                st.caption(f"📅 {media.get('uploaded_at', '')[:10]}")
                st.caption(f"👤 {media.get('uploader', 'Unknown')}")
                
                # Show tags
                if media.get("tags"):
                    tag_str = " ".join([f"#{tag}" for tag in media["tags"][:2]])
                    st.caption(f"🏷️ {tag_str}")
                
                st.markdown("---")
    else:
        st.info("📭 This album is empty")

def show_browse_interface(user, index):
    """Browse and search interface"""
    st.subheader("🔍 Browse & Search Media")
    
    # Simple search
    search_query = st.text_input("🔍 Search:", placeholder="Search by filename or tags...")
    
    if search_query:
        # Search media
        media = index.get("media", [])
        results = [m for m in media if 
                   search_query.lower() in m.get("filename", "").lower() or
                   search_query.lower() in " ".join(m.get("tags", [])).lower()]
        
        if results:
            st.success(f"📊 Found {len(results)} results")
            
            # Display results
            for media in results[:10]:  # Limit to 10 results
                with st.expander(f"📁 {media['filename']}", expanded=False):
                    if media["type"] == "photo":
                        file_path = os.path.join(PHOTO_DIR, media["filename"])
                        if os.path.exists(file_path):
                            st.image(file_path, width=300)
                    elif media["type"] == "video":
                        video_path = os.path.join(VIDEO_DIR, media["filename"])
                        if os.path.exists(video_path):
                            try:
                                with open(video_path, "rb") as f:
                                    video_bytes = f.read()
                                st.video(video_bytes)
                            except:
                                st.error("Cannot play video")
                    
                    st.write(f"📅 Uploaded: {media.get('uploaded_at', '')[:10]}")
                    st.write(f"👤 By: {media.get('uploader', 'Unknown')}")
        else:
            st.info("🔍 No results found")

def delete_album(album_id, user_email):
    """Delete an album and all its media"""
    index = _load_media_index()
    
    # Remove album
    index["albums"] = [a for a in index["albums"] if a["id"] != album_id]
    
    # Remove media files
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
            
            # Delete thumbnail
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
    log_audit_event(user_email, "DELETE", "ALBUM", album_id, {"media_count": len(album_media)})

# Media upload and viewing - Teachers upload/delete, all users view
import streamlit as st
import os
from utils.io import ensure_dir

PHOTO_DIR = "uploads/photos"  # Photos saved here automatically
VIDEO_DIR = "uploads/videos"  # Videos saved here automatically

def _list_dir_safe(path):
    """Safely list directory contents"""
    try:
        return sorted(os.listdir(path))
    except FileNotFoundError:
        return []

def _delete_file(file_path, file_name):
    """Delete a file and show confirmation"""
    try:
        os.remove(file_path)
        st.success(f"✅ **Deleted:** {file_name}")
        st.rerun()  # Refresh to show updated gallery
    except Exception as e:
        st.error(f"❌ **Error deleting {file_name}:** {str(e)}")

def main(user: dict):
    """
    Media management interface
    - Teachers: Upload + View + Delete
    - Students: View only
    FILES SAVED TO: uploads/photos and uploads/videos
    """
    st.header("📸 Department Media Center")
    st.markdown("---")

    # Teacher upload functionality
    if user["role"].lower() == "teacher":
        st.subheader("📤 Upload Media (Teacher Only)")
        
        # Ensure directories exist
        ensure_dir(PHOTO_DIR)
        ensure_dir(VIDEO_DIR)

        # File upload widget
        uploaded = st.file_uploader(
            "🎯 Choose Photo or Video:", 
            type=["jpg", "jpeg", "png", "mp4"],
            help="Supported formats: JPG, JPEG, PNG (photos) | MP4 (videos)"
        )
        
        if uploaded is not None:
            name = uploaded.name
            file_size = len(uploaded.getbuffer()) / (1024*1024)  # Size in MB
            
            # Determine file type and save location
            is_image = name.lower().endswith((".jpg", ".jpeg", ".png"))
            is_video = name.lower().endswith(".mp4")

            if is_image:
                save_dir = PHOTO_DIR
                file_type = "Photo"
                icon = "🖼️"
            elif is_video:
                save_dir = VIDEO_DIR
                file_type = "Video"
                icon = "🎥"
            else:
                st.error("❌ Unsupported file type. Please use JPG, PNG, or MP4.")
                return

            # Show file info
            st.info(f"{icon} **{file_type}:** {name} ({file_size:.2f} MB)")

            # Save file with duplicate handling
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, name)

            # Avoid overwriting by adding (n) suffix
            base, ext = os.path.splitext(save_path)
            i = 1
            final_path = save_path
            while os.path.exists(final_path):
                final_path = f"{base}({i}){ext}"
                i += 1

            # Save the file
            with open(final_path, "wb") as f:
                f.write(uploaded.getbuffer())
            
            st.success(f"✅ **Upload Successful!**")
            st.success(f"📁 Saved as: `{os.path.basename(final_path)}`")
            st.balloons()
    else:
        st.info("👁️ **Student Access:** View-only mode")

    # Media gallery (visible to all users)
    st.markdown("---")
    st.subheader("🖼️ Media Gallery")

    # Photos section
    st.write("### 📷 Photos")
    photos = _list_dir_safe(PHOTO_DIR)
    if photos:
        # Display photos in a grid (2 columns for better layout with delete buttons)
        for i in range(0, len(photos), 2):
            cols = st.columns(2)
            
            # Photo 1 (left column)
            if i < len(photos):
                photo = photos[i]
                photo_path = os.path.join(PHOTO_DIR, photo)
                with cols[0]:
                    try:
                        st.image(
                            photo_path, 
                            caption=photo, 
                            use_container_width=True
                        )
                        
                        # Teacher delete option
                        if user["role"].lower() == "teacher":
                            if st.button(f"🗑️ Delete", key=f"del_photo_{i}", help=f"Delete {photo}"):
                                if st.session_state.get(f"confirm_del_photo_{i}"):
                                    _delete_file(photo_path, photo)
                                else:
                                    st.session_state[f"confirm_del_photo_{i}"] = True
                                    st.warning("⚠️ Click delete again to confirm")
                                    st.rerun()
                            
                            # Reset confirmation if user didn't confirm
                            if st.session_state.get(f"confirm_del_photo_{i}") and not st.button(f"❌ Cancel", key=f"cancel_photo_{i}"):
                                pass
                            elif st.session_state.get(f"confirm_del_photo_{i}"):
                                st.session_state[f"confirm_del_photo_{i}"] = False
                                st.rerun()
                                
                    except Exception as e:
                        st.error(f"❌ Error loading {photo}: {str(e)}")
            
            # Photo 2 (right column)
            if i + 1 < len(photos):
                photo = photos[i + 1]
                photo_path = os.path.join(PHOTO_DIR, photo)
                with cols[1]:
                    try:
                        st.image(
                            photo_path, 
                            caption=photo, 
                            use_container_width=True
                        )
                        
                        # Teacher delete option
                        if user["role"].lower() == "teacher":
                            if st.button(f"🗑️ Delete", key=f"del_photo_{i+1}", help=f"Delete {photo}"):
                                if st.session_state.get(f"confirm_del_photo_{i+1}"):
                                    _delete_file(photo_path, photo)
                                else:
                                    st.session_state[f"confirm_del_photo_{i+1}"] = True
                                    st.warning("⚠️ Click delete again to confirm")
                                    st.rerun()
                            
                            # Reset confirmation if user didn't confirm
                            if st.session_state.get(f"confirm_del_photo_{i+1}") and not st.button(f"❌ Cancel", key=f"cancel_photo_{i+1}"):
                                pass
                            elif st.session_state.get(f"confirm_del_photo_{i+1}"):
                                st.session_state[f"confirm_del_photo_{i+1}"] = False
                                st.rerun()
                                
                    except Exception as e:
                        st.error(f"❌ Error loading {photo}: {str(e)}")
            
            st.markdown("---")
    else:
        st.info("📭 No photos uploaded yet")

    st.markdown("---")
    
    # Videos section  
    st.write("### 🎥 Videos")
    videos = _list_dir_safe(VIDEO_DIR)
    if videos:
        for j, video in enumerate(videos):
            video_path = os.path.join(VIDEO_DIR, video)
            
            # Video header with delete button for teachers
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**🎬 {video}**")
            with col2:
                if user["role"].lower() == "teacher":
                    if st.button(f"🗑️ Delete", key=f"del_video_{j}", help=f"Delete {video}"):
                        if st.session_state.get(f"confirm_del_video_{j}"):
                            _delete_file(video_path, video)
                        else:
                            st.session_state[f"confirm_del_video_{j}"] = True
                            st.warning("⚠️ Click delete again to confirm")
                            st.rerun()
                    
                    # Cancel confirmation
                    if st.session_state.get(f"confirm_del_video_{j}"):
                        if st.button(f"❌ Cancel", key=f"cancel_video_{j}"):
                            st.session_state[f"confirm_del_video_{j}"] = False
                            st.rerun()
            
            try:
                # Read video file and display
                with open(video_path, "rb") as video_file:
                    video_bytes = video_file.read()
                st.video(video_bytes)
            except Exception as e:
                st.error(f"❌ Error loading {video}: {str(e)}")
            st.markdown("---")
    else:
        st.info("📭 No videos uploaded yet")

    # Summary with delete all option for teachers
    total_files = len(photos) + len(videos)
    if total_files > 0:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.success(f"📊 **Total Media Files:** {total_files} ({len(photos)} photos, {len(videos)} videos)")
        
        with col2:
            if user["role"].lower() == "teacher" and total_files > 0:
                if st.button("🗑️ **Delete All Media**", type="secondary", help="Delete all photos and videos"):
                    if st.session_state.get("confirm_delete_all"):
                        # Delete all photos
                        for photo in photos:
                            try:
                                os.remove(os.path.join(PHOTO_DIR, photo))
                            except:
                                pass
                        
                        # Delete all videos
                        for video in videos:
                            try:
                                os.remove(os.path.join(VIDEO_DIR, video))
                            except:
                                pass
                        
                        st.success("✅ **All media deleted!**")
                        st.session_state["confirm_delete_all"] = False
                        st.rerun()
                    else:
                        st.session_state["confirm_delete_all"] = True
                        st.error("⚠️ **Click again to confirm deletion of ALL media files**")
                        st.rerun()
                
                # Cancel delete all
                if st.session_state.get("confirm_delete_all"):
                    if st.button("❌ Cancel Delete All"):
                        st.session_state["confirm_delete_all"] = False
                        st.rerun()

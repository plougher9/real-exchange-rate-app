    st.markdown("""
<style>
@keyframes ring { 0%,100%{transform:rotate(0)} 10%,30%,50%{transform:rotate(-4deg)}
                  20%,40%,60%{transform:rotate(4deg)} 70%{transform:rotate(0)} }
@keyframes pulse { 0%{box-shadow:0 0 0 0 rgba(46,204,113,.7)} 100%{box-shadow:0 0 0 22px rgba(46,204,113,0)} }
.phone { width:270px; margin:0 auto; border:10px solid #1c1c1e; border-radius:44px; outline:3px solid #b8892b;
  padding:34px 18px 26px; text-align:center; box-shadow:0 6px 18px rgba(0,0,0,.35);
  font-family:-apple-system,Helvetica,Arial,sans-serif; }
.phone.ring { background:linear-gradient(180deg,#2c3e50,#111); color:#fff; animation:ring 1.2s infinite; }
.phone.live { background:#fffdf5; color:#111; }
.notch { width:80px; height:20px; background:#1c1c1e; border-radius:12px; margin:-22px auto 16px; }
.avatar { width:74px; height:74px; border-radius:50%; background:#8e8e93; margin:8px auto; font-size:40px;
  line-height:74px; animation:pulse 1.3s infinite; }
.verdictbox { background:#fffdf5; border:1px solid #b8892b; border-left:8px solid #2f6b4f;
  border-radius:4px; padding:14px 18px; margin-top:14px; box-shadow:2px 3px 0 rgba(31,58,46,.15); }
.vtag { display:inline-block; padding:3px 12px; border-radius:12px; font-weight:700;
  font-size:.85rem; letter-spacing:.5px; margin-bottom:8px; }
.vbad { background:#a63d2f; color:#fffdf5; }
.vgood { background:#2f6b4f; color:#fffdf5; }
.vflat { background:#b8892b; color:#2b2110; }
</style>
""", unsafe_allow_html=True)

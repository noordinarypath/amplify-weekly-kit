# Team NOP Weekly kit

Builder for the Team NOP Weekly traveler newsletter. Code and font only. Graphics are pulled from Google Drive at run time; traveler data comes from the desk data repo. No traveler data is stored here.

    python3 -I tnw_build.py desk <desk-data.json> <YYYY-MM-DD>
    python3 -I tnw_build.py build <content.json> <assets_dir> <out_dir>

See the docstring at the top of tnw_build.py for the content.json fields and the assets the build expects.

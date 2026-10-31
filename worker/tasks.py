from .app import app


generate_panel_task = app.tasks["worker.app.generate_panel_task"]
review_panel_task = app.tasks["worker.app.review_panel_task"]
inpaint_panel_task = app.tasks["worker.app.inpaint_panel_task"]

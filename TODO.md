# Project To-Do List

This to-do list is based on the `development_plan.md` and breaks down the next steps into actionable tasks.

## 🎯 Priority 1: Complete Incremental Sync Feature

### 1. Implement Incremental Detection Algorithm
- [ ] Create a new `SyncDetector` class in a new `sync_detector.py` module.
- [x] Implement a method to fetch all objects from COS.
- [x] Implement a method to get all indexed files from `IndexManager`.
- [ ] Write the core logic to compare the COS objects and local index to find:
    - [ ] New files to download.
    - [ ] Updated files to re-download.
    - [ ] Locally deleted files to be aware of.
- [ ] Add filtering logic to the detection algorithm:
    - [ ] Filter by file size.
    - [ ] Filter by last modified time.
    - [ ] Add support for filtering by a date range.

### 2. Implement Smart Sync Strategy
- [ ] Create a `SyncExecutor` class in a new `sync_executor.py` module.
- [ ] Implement "automatic mode" to download all new/updated files.
- [ ] Implement "manual mode" to:
    - [ ] Display a list of new/updated files to the user.
    - [ ] Prompt the user to select which files to download.
- [ ] Implement "preview mode" to only display the file differences without downloading.
- [ ] Add a mechanism to pass the sync strategy (automatic, manual, preview) to the executor.

### 3. Implement Sync Status Management
- [ ] Add a `sync_history` table to the `download_index.db` database (as designed in the plan).
- [ ] Create a `SyncReporter` class in a new `sync_reporter.py` module.
- [ ] Implement a method to record the results of each sync operation in the `sync_history` table.
- [ ] Implement a method to generate a summary report of the sync operation.

### 4. Integration and Refinement
- [ ] Update `cos_enhanced_downloader.py` to incorporate the new sync features.
- [ ] Add command-line arguments to control the sync mode (`--sync-mode auto|manual|preview`).
- [x] Write unit tests for the new `SyncDetector`, `SyncExecutor`, and `SyncReporter` classes.
- [x] Update `development_plan.md` and `Development_status.md` to reflect the completion of the incremental sync feature.

## 🔐 Priority 2: Enhance Security

- [ ] Modify `_init_client` in `cos_enhanced_downloader.py` to prioritize reading credentials from environment variables (`COS_SECRET_ID`, `COS_SECRET_KEY`).
- [ ] Research and implement support for temporary credentials using Tencent Cloud's STS.

## ➕ Priority 3: Extend Object Operations

- [ ] Implement an `upload` function in `EnhancedCOSDownloader`.
- [ ] Implement a `delete` function in `EnhancedCOSDownloader`.
- [ ] Implement a function to view and modify object metadata.
- [ ] Add corresponding command-line arguments for these new operations.

## ✨ Priority 4: Improve User Experience

- [ ] Implement an interactive setup for `config.json` on the first run.
- [ ] Allow for multiple `--prefix` arguments for more flexible filtering.
- [ ] Add an `--exclude` argument to ignore certain files or directories.

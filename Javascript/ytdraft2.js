// -----------------------------------------------------------------
// CONFIG (you're safe to edit this)
// -----------------------------------------------------------------
// ~ GLOBAL CONFIG
// -----------------------------------------------------------------
const MODE = 'Publish Drafts'; // 'Publish Drafts' / 'Sort Playlist'
const DEBUG_LEVEL = 2; // 0 / 1 / 2				(0 = off, 1 = only debug/"verbose" log, 2 = general log)
const VERBOSE = false; // true / false			(enable to log full elements, disable to log only completed steps) 
const LOOP_PAGES = true; // true / false		(enable to loop through all pages)
// -----------------------------------------------------------------
// ~ PUBLISH CONFIG
// -----------------------------------------------------------------
const MADE_FOR_KIDS = false; // true / false;
const VISIBILITY = 'Private'; // 'Public' / 'Private' / 'Unlisted'
// -----------------------------------------------------------------
// ~ SORT PLAYLIST CONFIG
// -----------------------------------------------------------------
const SORTING_KEY = (one, other) => {
	return one.name.localeCompare(other.name, undefined, {numeric: true, sensitivity: 'base'});
};
// END OF CONFIG (not safe to edit stuff below)
// -----------------------------------------------------------------

// Art by Joan G. Stark
// .'"'.        ___,,,___        .'``.
// : (\  `."'"```         ```"'"-'  /) ;
//  :  \                         `./  .'
//   `.                            :.'
//     /        _         _        \
//    |         0}       {0         |
//    |         /         \         |
//    |        /           \        |
//    |       /             \       |
//     \     |      .-.      |     /
//      `.   | . . /   \ . . |   .'
//        `-._\.'.(     ).'./_.-'
//            `\'  `._.'  '/'
//              `. --'-- .'
//                `-...-'



// ----------------------------------
// COMMON  STUFF
// ---------------------------------
const TIMEOUT_STEP_MS = 20;
const DEFAULT_ELEMENT_TIMEOUT_MS = 2500;
function debugLog(...args) {
	if (!VERBOSE) { args = args.filter((data) => (typeof data == 'string')); }
	switch (DEBUG_LEVEL) {
		case 1:
			console.debug(...args);
		case 2:
			console.log(...args);
	}
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function untilElementNot(selector, callback=Null, baseEl=document, timeoutMs=DEFAULT_ELEMENT_TIMEOUT_MS) {
	//const  maxIterations = Math.ceil(timeoutMs / TIMEOUT_STEP_MS);
	//for (let i = 0; i < maxIterations; i++) {
	for (let timeout = timeoutMs; timeout > 0; timeout -= TIMEOUT_STEP_MS) {
		let element = baseEl.querySelector(selector);
		if (element != await callback()) {
			return element;
		}
		await sleep(TIMEOUT_STEP_MS);
	}
	return null;
}

async function untilElementClosed(selector, element, baseEl=document, timeoutMs=DEFAULT_ELEMENT_TIMEOUT_MS) {
	return await untilElementNot(selector, async () => element, baseEl, timeoutMs);
}

//const Null = () => Promise.resolve();
const Null = async () => null;
async function findElement(selector, baseEl=document, timeoutMs=DEFAULT_ELEMENT_TIMEOUT_MS) {
	const element = await untilElementNot(selector, Null, baseEl, timeoutMs);
	if (element) { return element; }
	; debugLog(`could not find ${selector} inside`, baseEl);
	return null;
}

function click(element=window) {
	if (!element) { return debugLog('cannot click on null'); }
	const event = new MouseEvent('click');
	element.dispatchEvent(event);
	; debugLog(element, 'clicked');
}

// ----------------------------------
// PUBLISH STUFF
// ----------------------------------
const VISIBILITY_PUBLISH_ORDER = {
	'Private': 0,
	'Unlisted': 1,
	'Public': 2
};

// SELECTORS
// ---------
const VIDEO_ROW_SELECTOR = 'ytcp-video-row';
const DRAFT_BUTTON_SELECTOR = '.edit-draft-button';
const DRAFT_MODAL_SELECTOR = '.style-scope.ytcp-uploads-dialog';
//const MADE_FOR_KIDS_SELECTOR = '#made-for-kids-group';
const RADIO_BUTTON_SELECTOR = 'tp-yt-paper-radio-button';
const VISIBILITY_STEPPER_SELECTOR = '#step-badge-3';
const VISIBILITY_PAPER_BUTTONS_SELECTOR = 'tp-yt-paper-radio-group';
const SAVE_BUTTON_SELECTOR = '#done-button';
//const SUCCESS_ELEMENT_SELECTOR = 'ytcp-video-thumbnail-with-info';
//const DIALOG_SELECTOR = 'ytcp-dialog.ytcp-video-share-dialog > tp-yt-paper-dialog:nth-child(1)';
const DIALOG_CLOSE_BUTTON_SELECTOR = 'tp-yt-iron-icon';
const NEXT_PAGE_BUTTON_SELECTOR = '#navigate-after';
// CHECKS
// --------
const PAGE_DESCRIPTION = '.page-description';
const DRAFT_DIALOG_OVERLAY = 'ytcp-uploads-dialog'; // or 'tp-yt-iron-overlay-backdrop.opened'

// class SuccessDialog {
// 	constructor(raw) {
// 		this.raw = raw;
// 	}

// 	async closeDialogButton() {
// 		return await findElement(DIALOG_CLOSE_BUTTON_SELECTOR, this.raw);
// 	}

// 	async close() {
// 		await sleep(50);
// 		; debugLog('closed');
// 	}
// }

class VisibilityModal {
	constructor(raw) {
		this.raw = raw;
	}

	async radioButtonGroup() {
		return await findElement(VISIBILITY_PAPER_BUTTONS_SELECTOR, this.raw);
	}

	async visibilityRadioButton() {
		const group = await this.radioButtonGroup();
		const value = VISIBILITY_PUBLISH_ORDER[VISIBILITY];
		return [...group.querySelectorAll(RADIO_BUTTON_SELECTOR)][value];
	}

	async setVisibility() {
		click(await this.visibilityRadioButton());
		; debugLog(`visibility set to ${VISIBILITY}`);
		await sleep(50);
	}

	async saveButton() {
		return await findElement(SAVE_BUTTON_SELECTOR, this.raw);
	}
	async isSaved() {
		await findElement(SUCCESS_ELEMENT_SELECTOR, document);
	}
	// async dialog() {
	// 	return await findElement(DIALOG_SELECTOR);
	// }
	async save() {
		click(await this.saveButton());
		await sleep(50);
		; debugLog('saved');
		// const dialogElement = await this.dialog();
		// const success = new SuccessDialog(dialogElement);
		return dialog;
	}
}

class DraftModal {
	constructor(raw) {
		this.raw = raw;
	}

	//async madeForKidsToggle() {
	//	return await findElement(MADE_FOR_KIDS_SELECTOR, this.raw);
	//}

	async getMadeForKidsPaperButton() {
		const nthChild = MADE_FOR_KIDS ? 1 : 2;
		return await findElement(`${RADIO_BUTTON_SELECTOR}:nth-child(${nthChild})`, this.raw);
	}

	async selectMadeForKids() {
		click(await this.getMadeForKidsPaperButton());
		await sleep(50);
		; debugLog(`"Made for kids" set to ${MADE_FOR_KIDS}`);
	}

	async visibilityStepper() {
		return await findElement(VISIBILITY_STEPPER_SELECTOR, this.raw);
	}

	async goToVisibility() {
		; debugLog('going to Visibility');
		await sleep(50);
		click(await this.visibilityStepper());
		const visibility = new VisibilityModal(this.raw);
		await sleep(50);
		await findElement(VISIBILITY_PAPER_BUTTONS_SELECTOR, visibility.raw);
		return visibility;
	}
}

class VideoRow {
	constructor(raw) {
		this.raw = raw;
	}

	get editDraftButton() {
		return findElement(DRAFT_BUTTON_SELECTOR, this.raw, 20);
	}

	async openDraft() {
		; debugLog('focusing draft button');
		click(await this.editDraftButton);
		return new DraftModal(await findElement(DRAFT_MODAL_SELECTOR));
	}
}


function getAllVideos() {
	return [...document.querySelectorAll(VIDEO_ROW_SELECTOR)].map((el) => new VideoRow(el));
}

async function getEditableVideos() {
	let editable = [];
	for (let video of getAllVideos()) {
		if ((await video.editDraftButton) !== null) {
			editable = [...editable, video];
		}
	}
	return editable;
}

async function publishDrafts() {
	const videos = await getEditableVideos();
	; debugLog(`found ${videos.length} videos`);
	; debugLog('starting in 1000ms...');
	await sleep(1000);
	for (let video of videos) {
		const draft = await video.openDraft();
		; debugLog({
			draft
		});
		await draft.selectMadeForKids();
		const visibility = await draft.goToVisibility();
		await visibility.setVisibility();
		const dialog = await findElement(DRAFT_DIALOG_OVERLAY);
		/*const dialog = */await visibility.save();
		//await dialog.close();
		await untilElementClosed(DRAFT_DIALOG_OVERLAY, dialog);
		; debugLog('published draft');
	}
}

async function getNextPageSelector() {
	return await findElement(NEXT_PAGE_BUTTON_SELECTOR);
}

async function getPageDescription() {
	return (await findElement(PAGE_DESCRIPTION)).innerText;
}

async function isNextPage(oldPageDescription, timeoutMs=5000) {  // Compare old page description to new page descriptions to check if page changes
	for (let timeout = timeoutMs; timeout > 0; timeout -= TIMEOUT_STEP_MS) {
		await sleep(TIMEOUT_STEP_MS);
		let newPageDescription = await getPageDescription();
		; debugLog(`${oldPageDescription} != ${newPageDescription} ${oldPageDescription != newPageDescription}`);
		if (oldPageDescription != newPageDescription) {
			return true;
		}
	}
	; debugLog('page description (i.e. "11-20 of 167") did not change');
	return null;
}

async function publishAllDrafts() {
	; debugLog('looping all pages...');
	await publishDrafts();
	let nextPageSelector = await getNextPageSelector();
	while (!nextPageSelector.disabled) {
		; debugLog('navigating to next page...');
		let pageDescription = await getPageDescription();
		click(nextPageSelector);
		if (await isNextPage(pageDescription)) {
			await publishDrafts();
			nextPageSelector = await getNextPageSelector();
		}
		else { return debugLog('could not continue on next page'); }
		; debugLog('continuing in next page...');
	}
	; debugLog('completed loop through all pages');
}

// ----------------------------------
// SORTING STUFF
// ----------------------------------
const SORTING_MENU_BUTTON_SELECTOR = 'button';
const SORTING_ITEM_MENU_SELECTOR = 'tp-yt-paper-listbox#items';
const SORTING_ITEM_MENU_ITEM_SELECTOR = 'ytd-menu-service-item-renderer';
const MOVE_TO_TOP_INDEX = 4;
const MOVE_TO_BOTTOM_INDEX = 5;

class SortingDialog {
	constructor(raw) {
		this.raw = raw;
	}

	async anyMenuItem() {
		const item =  await findElement(SORTING_ITEM_MENU_ITEM_SELECTOR, this.raw);
		if (item === null) {
			throw new Error("could not locate any menu item");
		}
		return item;
	}

	menuItems() {
		return [...this.raw.querySelectorAll(SORTING_ITEM_MENU_ITEM_SELECTOR)];
	}

	async moveToTop() {
		click(this.menuItems()[MOVE_TO_TOP_INDEX]);
	}

	async moveToBottom() {
		click(this.menuItems()[MOVE_TO_BOTTOM_INDEX]);
	}
}
class PlaylistVideo {
	constructor(raw) {
		this.raw = raw;
	}
	get name() {
		return this.raw.querySelector('#video-title').textContent;
	}
	async dialog() {
		return this.raw.querySelector(SORTING_MENU_BUTTON_SELECTOR);
	}

	async openDialog() {
		click(await this.dialog());
		const dialog = new SortingDialog(await findElement(SORTING_ITEM_MENU_SELECTOR));
		await dialog.anyMenuItem();
		return dialog;
	}

}
async function playlistVideos() {
	return [...document.querySelectorAll('ytd-playlist-video-renderer')]
		.map((el) => new PlaylistVideo(el));
}
async function sortPlaylist() {
	; debugLog('sorting playlist');
	const videos = await playlistVideos();
	; debugLog(`found ${videos.length} videos`);
	videos.sort(SORTING_KEY);
	const videoNames = videos.map((v) => v.name);

	let index = 1;
	for (let name of videoNames) {
		; debugLog({index, name});
		const video = videos.find((v) => v.name === name);
		const dialog = await video.openDialog();
		await dialog.moveToBottom();
		await sleep(1000);
		index += 1;
	}

}


// ----------------------------------
// ENTRY POINT
// ----------------------------------
({
	'Publish Drafts': LOOP_PAGES ? publishAllDrafts : publishDrafts,
	'Sort Playlist': sortPlaylist,
})[MODE]();
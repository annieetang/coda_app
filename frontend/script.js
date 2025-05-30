document.querySelector("button").addEventListener("click", function(event) {
  event.preventDefault();
});

async function loadOriginal() {
    console.log("Loading original MusicXML...");
    osmd
    // const response = await fetch(`http://localhost:5000/music/${filename}`);
    .load("../music/test_score.mxl")
    .then(
      function() {
        osmd.render();
      }
    );
}

// let fileSelector = document.getElementById("fileSelector");
let fileSelected = "";
const loadScoreBtn = document.getElementById("loadScoreBtn");
const practiceBtn = document.getElementById("practiceBtn");

// Enable/disable buttons based on file selection
if (fileSelected) {
  fileSelected.addEventListener("change", function() {
    const valid = fileSelected && fileSelected !== "";
    loadScoreBtn.disabled = !valid;
    // only load the practiceBtn after the loadScoreBtn is clicked
    practiceBtn.disabled = true;
  });
}

window.onload = async function () {
    await loadLibrary();
    setupFileUpload();
};

async function loadLibrary() {
    const res = await fetch("http://127.0.0.1:5000/list_files");
    const files = await res.json();
    const libraryGrid = document.getElementById("libraryGrid");
    
    files.forEach(async (file) => {
        const card = document.createElement("div");
        card.className = "score-card";
        
        // Create preview container
        const preview = document.createElement("div");
        preview.className = "score-preview";
        
        // Create OSMD instance for preview
        const previewId = `preview-${file.replace(/[^a-zA-Z0-9]/g, '-')}`;
        preview.id = previewId;
        
        // Create score info section
        const info = document.createElement("div");
        info.className = "score-info";
        
        // Format the title (remove extension and replace underscores/hyphens with spaces)
        const title = file.replace(/\.(xml|mxl)$/, '').replace(/[_-]/g, ' ');
        
        info.innerHTML = `
            <div class="score-title">${title}</div>
            <div class="score-metadata">[composer here]</div>
        `;
        
        card.appendChild(preview);
        card.appendChild(info);
        
        // Add click handler
        card.onclick = async () => {
            fileSelected = file;
            await loadScore(file);
            showInitialScreen();
        };
        
        libraryGrid.appendChild(card);
        
        // Load score preview
        console.log(previewId)
        const osmd = new opensheetmusicdisplay.OpenSheetMusicDisplay(
            previewId,
            {
                // drawingParameters: "compact",
                drawPartNames: false,
                drawTitle: false, // temporary solution...
                drawMeasureNumbers: false
            }
        );
        
        try {
            await osmd.load("../music/" + file, tempTitle = title);
            osmd.zoom = 0.4; // Adjust this value to fit your needs
            osmd.title = title;
            await osmd.render();
        } catch (error) {
            console.error("Failed to load preview for", file, error);
            preview.innerHTML = '<div class="error">Preview not available</div>';
        }
    });
}

// Loading overlay helpers
function showLoading() {
  document.getElementById('loadingOverlay').style.display = 'flex';
}
function hideLoading() {
  document.getElementById('loadingOverlay').style.display = 'none';
}

async function loadScore(filename) {
    showLoading();
    try {
        console.log("Loading score:", filename);
        // Set the piece title in breadcrumb and score display
        const title = filename.replace('.xml', '').replace('.mxl', '').replace(/[_-]/g, ' ');
        document.getElementById('pieceTitle').textContent = title;
        document.getElementById('scoreTitleDisplay').textContent = title;

        // Enable practice button
        document.getElementById('practiceBtn').disabled = false;
        
        await loadSoundslice("../music/" + filename);
    } finally {
        hideLoading();
    }
}

// Update showInitialScreen to handle navigation from library
function showInitialScreen() {
    showScreen('initialScreen');
    // No need to reload Soundslice here as it's handled in loadScore
}

var bar_count = 0;
var start_measure = 1;
var end_measure = 1;
var start_second = 0;
var end_second = 0;
var total_seconds = 0;
var bpm = 0;
var notation_loaded = false;
var loopChangeTimer = null;

window.addEventListener('message', async function(event) {
  var cmd;
  try {
    cmd = JSON.parse(event.data);
  } catch (e) {
    console.warn('Invalid JSON received:', event.data);
    return;
  }
  // NOTE: start and end measures are still a bit buggy, with the "focus" and also the range if end_second < 0, (i.e., when the loop seconds are set to -1 and -1)
  if (cmd.method === 'ssLoopChange') {
    console.log('loop changed to ' + cmd.arg);
    start_second = cmd.arg[0];
    end_second = cmd.arg[1];

    if (start_second < 0) {
      start_second = 0;
    }
    if (end_second < 0) {
      // end_second = total_seconds;
      end_second = start_second;
    }

    // Clear any existing timer
    if (loopChangeTimer) {
      clearTimeout(loopChangeTimer);
    }

    // Set new timer
    loopChangeTimer = setTimeout(async () => {
      // post a message to api to get measure
      console.log("making API call to get measures from seconds");
      var s_measure = await get_measure(start_second);
      document.getElementById("startMeasure").value = s_measure;

      var e_measure = await get_measure(end_second);

      if (e_measure < s_measure) {
        e_measure = s_measure;
      }

      document.getElementById("endMeasure").value = e_measure;
      loopChangeTimer = null;
    }, 500); // Wait 1 second after last loop change

  } else if (cmd.method === 'ssSeek') {
    // console.log('seek to ' + cmd.arg);
    start_second = cmd.arg;
    var s_measure = await get_measure(start_second);
    // console.log('start measure is ' + s_measure);

    // if it's just a seek, set end measure equal to the start measure
    document.getElementById("startMeasure").value = s_measure;
    document.getElementById("endMeasure").value = s_measure;

  }
  if (cmd.method === 'ssCurrentBar') {
    console.log('Current bar is ' + cmd.arg);
  }
  if (cmd.method === 'ssBarCount') {
    console.log('Total bar count is ' + cmd.arg);
    bar_count = cmd.arg;
    if (cmd.arg == 0){
      // recall the api 
      postMessageAfterLoad(document.getElementById('ssembed'));
    }

    // this.document.getElementById("endMeasure").value = bar_count;
    // this.document.getElementById("endMeasure").max = bar_count;
    // this.document.getElementById("startMeasure").max = bar_count;
  }
  if (cmd.method === 'ssDuration') {
    console.log('Duration is ' + cmd.arg);
    total_seconds = cmd.arg;
    if (end_second === 0) {
      end_second = total_seconds;
    }
  }
  if (cmd.method === 'ssSpeed') {
    console.log('Speed is ' + cmd.arg);
  }
  if (cmd.method === 'ssNotationVisibility') {
    console.log('Notation visibility is ' + cmd.arg);
    notation_loaded = cmd.arg;
  }
});

async function get_measure(second) {
  // console.log("Getting measure for second:", second);
  // call get_measure from the server
  const response = await fetch("http://127.0.0.1:5000/get_measure_from_second", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename: fileSelected, second: second })
  });
  if (!response.ok) {
    console.error("Failed to get measure:", response.statusText);
    return;
  }
  const data = await response.json();
  return data.measure_number;
}

// Helper function to handle Soundslice iframe loading and notation visibility checks
async function loadSoundsliceIframe(src, container, maxAttempts = 10) {
  let loaded = false;
  let attempts = 0;
  
  while (!loaded && attempts < maxAttempts) {
    console.log("Loading attempt:", attempts + 1);
    
    const iframe = document.createElement("iframe");
    iframe.id = "ssembed";
    iframe.src = src;
    iframe.width = "85%";
    // center the iframe
    iframe.style.margin = "0 auto";
    // if this is the miniplayer, height is - 300, if it's the main one, it should be - 250
    if (container.id === "soundsliceContainer") {
      iframe.height = window.innerHeight - 280;
    } else {
      iframe.height = window.innerHeight - 300;
    }
    iframe.style.border = "0";
    iframe.allowfullscreen = true;
    
    try {
      loaded = await new Promise((resolve) => {
        iframe.onload = () => {
          setTimeout(() => {
            if (!iframe.contentWindow) {
              console.log("No iframe content window");
              return resolve(false);
            }
            
            // TODO: clean this up, too many api calls I think
            try {
              console.log("Checking notation visibility, attempt:", attempts + 1);
              iframe.contentWindow.postMessage('{"method": "getNotationVisibility"}', 'https://www.soundslice.com');
              
              let checkCount = 0;
              const maxChecks = 5;
              
              const checkNotation = () => {
                if (checkCount >= maxChecks) {
                  console.log("Max checks reached for this attempt");
                  return resolve(false);
                }
                
                checkCount++;
                if (notation_loaded) {
                  console.log("Notation loaded successfully!");
                  postMessageAfterLoad(iframe);
                  resolve(true);
                } else {
                  console.log("Notation not loaded yet, check", checkCount, "of", maxChecks);
                  iframe.contentWindow.postMessage('{"method": "getNotationVisibility"}', 'https://www.soundslice.com');
                  setTimeout(checkNotation, 500);
                }
              };
              
              checkNotation();
            } catch (e) {
              console.error("Error in visibility check:", e);
              resolve(false);
            }
          }, 1000);
        };
        container.appendChild(iframe);
      });
      
      if (!loaded) {
        container.innerHTML = "";
        await new Promise(resolve => setTimeout(resolve, 2000));
      }
    } catch (e) {
      console.error("Error loading iframe:", e);
      loaded = false;
    }
    
    attempts++;
  }
  
  if (!loaded) {
    container.innerHTML = "<div class='error'>Failed to load notation after several attempts</div>";
  }
  
  return loaded;
}

async function getSliceHash(filename, musicxml = null) {
  const payload = musicxml ? { filename, musicxml } : { filename };
  const response = await fetch("http://127.0.0.1:5000/get_slicehash", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  
  if (!response.ok) {
    console.error("Failed to get Soundslice data:", response.statusText);
    return null;
  }
  
  const data = await response.json();
  return data.slicehash;
}

async function loadSoundslice(filename) {
  console.log("Loading Soundslice...");
  
  const slicehash = await getSliceHash(filename);
  if (!slicehash) return;
  
  console.log("Slicehash:", slicehash);
  const src = `https://www.soundslice.com/slices/${slicehash}/embed/?api=1`;
  const container = document.getElementById("soundsliceContainer");
  container.innerHTML = "";
  
  await loadSoundsliceIframe(src, container);
}

async function loadSoundsliceMiniplayer(filename, musicxml) {
  console.log("Loading Soundslice Miniplayer...");
  
  const container = document.getElementById("soundsliceMiniplayerContainer");
  container.innerHTML = "";
  
  const slicehash = await getSliceHash(filename, musicxml);
  if (!slicehash) {
    container.innerHTML = "<div class='error'>Failed to create slice</div>";
    return;
  }
  
  console.log("Slicehash:", slicehash);
  const src = `https://www.soundslice.com/slices/${slicehash}/embed/?api=1`;
  
  await loadSoundsliceIframe(src, container);
}

async function postMessageAfterLoad(iframe) {
  // post a message to the iframe to get the current bar
  var ssiframe = document.getElementById('ssembed').contentWindow;
  ssiframe.postMessage('{"method": "getCurrentBar"}', 'https://www.soundslice.com');
  ssiframe.postMessage('{"method": "getBarCount"}', 'https://www.soundslice.com');
  ssiframe.postMessage('{"method": "getDuration"}', 'https://www.soundslice.com');
  ssiframe.postMessage('{"method": "getSpeed}', 'https://www.soundslice.com');
  // show title at top of notation
  // ssiframe.postMessage('{"method": "setTrackVisibility", "type": 13, "arg": 1}', 'https://www.soundslice.com');
}

async function testSoundsliceCreate() {
  const response = await fetch("http://127.0.0.1:5000/load_soundslice", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename: fileSelected })
  });
  if (!response.ok) {
    console.error("Failed to get Soundslice data:", response.statusText);
    return;
  }
  const data = await response.json();
  console.log("Soundslice data:", data);
}

// Global variables
let currentExercises = [];
let currentExerciseIndex = 0;

// Screen management
let currentOsmdInstance = null;

async function cleanupAndRenderOSMD(container, xml) {
    // Cleanup previous instance if it exists
    if (currentOsmdInstance) {
        currentOsmdInstance.clear();
        currentOsmdInstance = null;
    }

    // Clear the container
    container.innerHTML = '';
    
    // Create new instance
    currentOsmdInstance = new opensheetmusicdisplay.OpenSheetMusicDisplay(
        container.id,
        { drawingParameters: "compacttight", autoResize: true }
    );
    
    try {
        await currentOsmdInstance.load(xml);
        await currentOsmdInstance.render();
    } catch (error) {
        console.error("Error rendering OSMD:", error);
        container.innerHTML = "<div class='error'>Failed to render notation</div>";
    }
}

function showScreen(screenId) {
    // Clean up OSMD when leaving exercise screen
    if (screenId !== 'exerciseScreen' && currentOsmdInstance) {
        currentOsmdInstance.clear();
        currentOsmdInstance = null;
    }
    
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });
    document.getElementById(screenId).classList.add('active');
    
    // Update breadcrumb visibility based on screen
    if (screenId === 'libraryScreen') {
        document.getElementById('pieceTitle').textContent = '';
        document.getElementById('practiceNav').textContent = '';
        document.getElementById('exerciseNav').textContent = '';
    } else if (screenId === 'initialScreen') {
        document.getElementById('practiceNav').textContent = '';
        document.getElementById('exerciseNav').textContent = '';
    } else if (screenId === 'exerciseGridScreen') {
        document.getElementById('exerciseNav').textContent = '';
    }
}

function showLibraryScreen() {
    showScreen('libraryScreen');
}

function showExerciseGrid() {
    showScreen('exerciseGridScreen');
}

async function showExerciseScreen(exercise_filename, exercise) {
  showScreen('exerciseScreen');
  // load the soundslice miniplayer embed
  await loadSoundsliceMiniplayer(exercise_filename, exercise.xml);
}

// File loading and initial setup
async function loadSelected() {
    let selectedFile = fileSelected;
    if (!selectedFile || selectedFile === "") {
        practiceBtn.disabled = true;
        return;
    }
    
    console.log("Loading selected:", selectedFile);
    // Set the piece title in breadcrumb
    const title = selectedFile.replace('.xml', '').replace('.mxl', '');
    document.getElementById('pieceTitle').textContent = title;

    // Enable practice button after successful load
    practiceBtn.disabled = false;
    selectedFile = "../music/" + selectedFile;
    
    await loadSoundslice(selectedFile);
}

// Exercise generation and display
async function generateExercises() {
    showLoading();
    try {
        const startMeasure = parseInt(document.getElementById("startMeasure").value);
        const endMeasure = parseInt(document.getElementById("endMeasure").value);
        
        console.log("Generating exercises for range:", startMeasure, endMeasure);
        
        // Update breadcrumb
        document.getElementById('practiceNav').textContent = 'Practice';
        document.getElementById('exerciseNav').textContent = '';
        
        const response = await fetch("http://127.0.0.1:5000/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                filename: "../music/" + fileSelected,
                start_measure: startMeasure,
                end_measure: endMeasure
            })
        });

        if (!response.ok) {
            console.error("Failed to generate exercises:", response.statusText);
            return;
        }

        const response_json = await response.json();
        currentExercises = [];
        
        // Clear existing grid
        const grid = document.getElementById('exerciseGrid');
        grid.innerHTML = '';

        // get the start and end measures from the json
        let start = response_json.start_measure;
        let end = response_json.end_measure;
        let exercises = response_json.exercises;

        // Create filter buttons for each category
        const filterContainer = document.getElementById('filterContainer');
        filterContainer.innerHTML = '<button class="filter-button active" data-category="all">All Exercises</button>';
        
        // Get unique categories
        const categories = Object.keys(exercises).reverse();
        
        // Create filter buttons
        categories.forEach(category => {
            const button = document.createElement('button');
            button.className = 'filter-button';
            button.setAttribute('data-category', category);
            button.textContent = category;
            filterContainer.appendChild(button);
        });

        // Add click handlers to filter buttons
        const filterButtons = document.querySelectorAll('.filter-button');
        filterButtons.forEach(button => {
            button.addEventListener('click', () => {
                // Update active state of buttons
                filterButtons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');

                // Show/hide exercise containers based on category
                const selectedCategory = button.getAttribute('data-category');
                const containers = document.querySelectorAll('.exercise-type-container');
                containers.forEach(container => {
                    if (selectedCategory === 'all' || container.getAttribute('data-category') === selectedCategory) {
                        container.classList.remove('hidden-category');
                    } else {
                        container.classList.add('hidden-category');
                    }
                });
            });
        });

        // Create exercise cards
        // First create a container for each type
        const typeContainers = {};
        
        for (const [type, xmlList] of Object.entries(Object.fromEntries(Object.entries(exercises).reverse()))) {
            if (!xmlList || xmlList.length === 0) continue;
            
            // Create a container for this type
            const typeContainer = document.createElement('div');
            typeContainer.className = 'exercise-type-container';
            typeContainer.setAttribute('data-category', type);
            
            // Add a header for this type
            const typeHeader = document.createElement('h2');
            typeHeader.className = 'exercise-type-header';
            typeHeader.textContent = type;
            typeContainer.appendChild(typeHeader);
            
            // Create a grid container for this type's exercises
            const typeGrid = document.createElement('div');
            typeGrid.className = 'exercise-type-grid';
            typeContainer.appendChild(typeGrid);
            
            // Add the type container to the main grid
            grid.appendChild(typeContainer);
            typeContainers[type] = typeGrid;
            
            xmlList.forEach(([description, xml], index) => {
                if (!xml) return;
                
                const exercise = {
                    type,
                    xml,
                    index: currentExercises.length,
                    description
                };
                currentExercises.push(exercise);
                
                // Create preview card
                const card = document.createElement('div');
                card.className = 'exercise-card';

                // create a description place inside the card
                const descriptionContainer = document.createElement('div');
                descriptionContainer.className = 'exercise-description';
                descriptionContainer.innerHTML = description;
                
                // Create container for OSMD
                const previewContainer = document.createElement('div');
                previewContainer.id = `preview-${exercise.index}`;
                previewContainer.className = 'exercise-preview';
                
                card.innerHTML = `<h3 class="exercise-title">Exercise ${index + 1}</h3>`;
                card.appendChild(descriptionContainer);
                card.appendChild(previewContainer);
                typeContainers[type].appendChild(card);
                card.onclick = () => showExercise(exercise.index, start, end);
                
                // Render preview after container is in DOM
                const preview = new opensheetmusicdisplay.OpenSheetMusicDisplay(
                    `preview-${exercise.index}`,
                    { drawingParameters: "compacttight" }
                );
                preview.load(xml)
                    .then(() => preview.render())
                    .catch(error => {
                        console.error("Failed to load preview:", error);
                    });
            });
        }
        showExerciseGrid();
    } finally {
        hideLoading();
    }
}

// Single exercise display
async function showExercise(index, start_m, end_m) {
    // showLoading();
    try {
        currentExerciseIndex = index;
        const exercise = currentExercises[index];
        
        // Update breadcrumb and title
        const exerciseTitle = `${exercise.type} - Exercise ${currentExerciseIndex + 1}`;
        document.getElementById('exerciseNav').textContent = exerciseTitle;
        
        // Show the exercise screen
        showScreen('exerciseScreen');
        
        // Update the exercise content
        const exerciseScreen = document.getElementById('exerciseScreen');
        const contentContainer = exerciseScreen.querySelector('.max-w-6xl');
        
        // Update title and description
        contentContainer.querySelector('.exercise-title').textContent = exerciseTitle;
        contentContainer.querySelector('.exercise-description').textContent = exercise.description;

        // Generate the filename for reference
        exercise_filename_raw = fileSelected.replace('.mxl', '') + "_" + start_m + "_" + end_m + "_" + exercise.index + ".mxl";
        console.log("Exercise filename raw:", exercise_filename_raw);
        exercise_filename = exercise_filename_raw.replace(/ /g, '_');

        // Initialize OSMD view
        const osmdContainer = document.getElementById('osmdContainer');
        await cleanupAndRenderOSMD(osmdContainer, exercise.xml);

        // Reset notation loaded state and disable toggle
        notation_loaded = false;
        const viewToggleLabel = document.querySelector('.switch');
        const viewToggleText = viewToggleLabel.nextElementSibling;
        viewToggleLabel.classList.add('disabled');
        const viewToggle = document.getElementById('viewToggle');
        viewToggle.disabled = true;
        viewToggle.checked = false;
        const viewToggleSlider = viewToggle.nextElementSibling;
        viewToggleSlider.classList.add('disabled');
        viewToggleText.textContent = 'Loading Interactive Player...';

        // Start loading Soundslice in the background
        const soundsliceContainer = document.getElementById('soundsliceMiniplayerContainer');
        soundsliceContainer.className = 'view-container';
        await loadSoundsliceMiniplayer(exercise_filename, exercise.xml);
        
        // Set up toggle behavior
        const newViewToggle = viewToggle.cloneNode(true);
        viewToggle.parentNode.replaceChild(newViewToggle, viewToggle);
        
        // Add new event listener
        newViewToggle.addEventListener('change', async function() {
            if (this.checked) {
                osmdContainer.classList.remove('active');
                soundsliceContainer.classList.add('active');
            } else {
                soundsliceContainer.classList.remove('active');
                osmdContainer.classList.add('active');
            }
        });

        // Set up an interval to check for notation loading
        const checkNotationInterval = setInterval(() => {
            if (notation_loaded) {
                viewToggleLabel.classList.remove('disabled');
                newViewToggle.disabled = false;
                newViewToggle.nextElementSibling.classList.remove('disabled');
                viewToggleText.textContent = 'Show Interactive Player';
                clearInterval(checkNotationInterval);
            }
        }, 100);

        // Clear interval after 30 seconds to prevent infinite checking
        setTimeout(() => {
            if (!notation_loaded) {
                clearInterval(checkNotationInterval);
                viewToggleText.textContent = 'Interactive Player Failed to Load';
            }
        }, 30000);

        // Update navigation buttons
        updateNavigationButtons();
    } finally {
        hideLoading();
    }
}

function updateNavigationButtons() {
    const prevButton = document.querySelector('.nav-controls button:first-child');
    const nextButton = document.querySelector('.nav-controls button:last-child');
    
    prevButton.style.visibility = currentExerciseIndex > 0 ? 'visible' : 'hidden';
    nextButton.style.visibility = currentExerciseIndex < currentExercises.length - 1 ? 'visible' : 'hidden';
}

async function previousExercise() {
    if (currentExerciseIndex > 0) {
        await showExercise(currentExerciseIndex - 1);
    }
}

async function nextExercise() {
    if (currentExerciseIndex < currentExercises.length - 1) {
        await showExercise(currentExerciseIndex + 1);
    }
}

async function manipulateAndRender() {
    const startMeasure = parseInt(document.getElementById("startMeasure").value);
    const endMeasure = parseInt(document.getElementById("endMeasure").value);
    console.log("Manipulating and rendering MusicXML with range:", startMeasure, endMeasure);
    console.log("Manipulating and rendering MusicXML...");
    const file = '../music/' + fileSelected;
    const response = await fetch("http://127.0.0.1:5000/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      // body: JSON.stringify({ filename: '../music/' + fileSelected })
      body: JSON.stringify({ filename: file, start_measure: startMeasure, end_measure: endMeasure })
    });

    if (!response.ok) {
      console.error("Failed to get manipulated XML:", response.statusText);
      return;
    }

    const musicXmlList = await response.json();
    // musicXmlList is a hashmap with key as the type of score and value as the xml
    // display the key before the xml
    console.log("MusicXML List:", musicXmlList);
    for (const [key, xmlList] of Object.entries(musicXmlList)) {
      console.log("Key:", key);
      // console.log("XML:", xml);

      // Create a header for the score type
      const header = document.createElement("h2");
      header.textContent = key;
      document.getElementById("scoreList").appendChild(header);
      
      for (let i = 0; i < xmlList.length; i++) {
        const xml = xmlList[i];
        
        if (!xml) {
          // console.error("Empty XML for key:", key);
          // const text = document.createElement("p");
          // text.textContent = "[This level is same as the sub-level, not displaying since it's duplicate]";
          // document.getElementById("scoreList").appendChild(text);
          // remove section header that was just created
          header.remove();
          continue;
        }
        
        // Create a unique container for this score
        const container = document.createElement("div");
        container.id = `osmd-container-${key}-${i}`;
        container.style.marginBottom = "40px"; // optional spacing
        document.getElementById("scoreList").appendChild(container);
        
        // Create and render OSMD instance
        const osmd = new opensheetmusicdisplay.OpenSheetMusicDisplay(container.id, {
          drawingParameters: "compact" // or "default" if you want full spacing
        });
        
        await osmd.load(xml);
        osmd.render();
      }
    }

}

function clearScoreList() {
  // remove the scorelist div
  const scoreList = document.getElementById("scoreList");
  while (scoreList.firstChild) {
    scoreList.removeChild(scoreList.firstChild);
  }
}

function setupFileUpload() {
    const uploadInput = document.getElementById('scoreUpload');
    uploadInput.addEventListener('change', handleFileUpload);
}

async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file type
    const validTypes = ['.xml', '.musicxml', '.mxl'];
    const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
    if (!validTypes.includes(fileExtension)) {
        alert('Please upload a valid MusicXML file (.xml, .musicxml, or .mxl)');
        return;
    }

    // Create form data
    const formData = new FormData();
    formData.append('file', file);

    // Get upload container reference before try block
    const uploadContainer = document.querySelector('.upload-container');
    let progress = null;

    try {
        // Show upload progress
        progress = document.createElement('div');
        progress.className = 'upload-progress';
        const progressBar = document.createElement('div');
        progressBar.className = 'upload-progress-bar';
        progress.appendChild(progressBar);
        uploadContainer.appendChild(progress);

        // Upload file
        const response = await fetch('http://127.0.0.1:5000/upload_score', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Upload failed');
        }

        // Show success state
        progressBar.style.width = '100%';
        setTimeout(() => {
            if (progress && progress.parentNode) {
                progress.remove();
            }
            // Reload library to show new file
            loadLibrary();
        }, 1000);

    } catch (error) {
        console.error('Upload failed:', error);
        alert(error.message || 'Failed to upload file. Please try again.');
        if (progress && progress.parentNode) {
            progress.remove();
        }
    }

    // Reset file input
    event.target.value = '';
}
document.addEventListener('DOMContentLoaded', function() { // NOSONAR
    // --- CSRF Token pour les requêtes AJAX ---
    const csrfToken = "{{ csrf_token }}";

    // --- Fonctions de synchronisation Backend (AJAX API) ---
    async function syncTaskCompletion(taskId, isCompleted) {
        try {
            // Remplacez cette URL par votre véritable route Django (ex: /api/tasks/toggle-completion/) // NOSONAR
            await fetch('/api/tasks/toggle-completion/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify({ task_id: taskId, is_completed: isCompleted })
            });
        } catch (e) {
            console.info("Synchro backend (complétion) ignorée (mode hors-ligne ou endpoint manquant).");
        }
    }

    async function syncLocalActivity(activityData, action = "save") {
        try {
            // Endpoints théoriques : /api/tasks/save-local/ ou /api/tasks/delete-local/ // NOSONAR
            const endpoint = action === "save" ? '/api/tasks/save-local/' : '/api/tasks/delete-local/';
            await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify(activityData)
            });
        } catch (e) {
            console.info(`Synchro backend (${action}) ignorée (mode hors-ligne ou endpoint manquant).`);
        }
    }

    function addHistoryEntry(taskId, action) {
        const activity = backendActivities.find(a => String(a.id) === String(taskId));
        if (!activity) return;

        if (!activity.history) {
            activity.history = [];
        }

        activity.history.push({
            action: action,
            timestamp: new Date().toISOString()
        });

        // Si c'est une tâche locale, on met à jour le localStorage
        if (String(activity.id).startsWith('local_')) {
            let savedLocalActivities = JSON.parse(localStorage.getItem('creme_local_activities') || '[]');
            const localActIndex = savedLocalActivities.findIndex(a => a.id === activity.id);
            if (localActIndex > -1) {
                savedLocalActivities[localActIndex] = activity;
                localStorage.setItem('creme_local_activities', JSON.stringify(savedLocalActivities));
            }
        }
    }
    // --- Gestion des tâches accomplies ---
    const COMPLETED_TASKS_KEY = 'creme_completed_tasks';

    function getCompletedTasks() {
        try {
            const tasks = JSON.parse(localStorage.getItem(COMPLETED_TASKS_KEY) || '{}');
            const timeLimit = new Date().getTime() - (365 * 24 * 60 * 60 * 1000);
            const filteredTasks = {};
            for (const taskId in tasks) {
                if (tasks[taskId] > timeLimit) {
                    filteredTasks[taskId] = tasks[taskId];
                }
            }
            localStorage.setItem(COMPLETED_TASKS_KEY, JSON.stringify(filteredTasks));
            return Object.keys(filteredTasks);
        } catch (e) {
            return [];
        }
    }

    function toggleTaskCompletion(taskId, isCompleted) {
        const tasks = JSON.parse(localStorage.getItem(COMPLETED_TASKS_KEY) || '{}');
        if (isCompleted) {
            tasks[taskId] = new Date().getTime();
        } else {
            delete tasks[taskId];
        }
        localStorage.setItem(COMPLETED_TASKS_KEY, JSON.stringify(tasks));
        
        // Appel AJAX pour synchroniser l'état avec la base de données
        syncTaskCompletion(taskId, isCompleted);
    }

    // --- Affichage des notifications (Toasts) ---
    function showToast(message, type = 'success') {
        const toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) return;
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        let icon = '✅';
        if (type === 'error') icon = '❌';
        else if (type === 'warning') icon = '⚠️';
        
        toast.innerHTML = `<span style="font-size:1.2em;">${icon}</span> <span>${message}</span>`;
        
        toastContainer.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('fade-out');
            toast.addEventListener('animationend', () => toast.remove());
        }, 3000);
    }

   // Centre de notifications
   const NOTIFICATIONS_KEY = 'creme_notifications';
   const notificationBellIcon = document.getElementById('notificationBellIcon');
   const notificationCountBadge = document.getElementById('notificationCountBadge');
   const notificationPanel = document.getElementById('notificationPanel');
   const NotificationList = document.getElementById('notificationList');
   const clearNotificationBtn = document.getElementById('clearNotificationsBtn');

   const showAllAlertsBtn = document.getElementById('showAllAlertsBtn');
    if (showAllAlertsBtn) {
        showAllAlertsBtn.addEventListener('click', () => {
            notificationPanel.style.display = 'none';
            window.showGlobalAlerts();
        });
    }

   let notifications = [];

   function loadNotifications() {
    try {
        const stored = JSON.parse(localStorage.getItem(NOTIFICATIONS_KEY) || '[]');
        const timeLimit = new Date().getTime() - (7*24*60*60*1000); // garder les notifs 7 jours
        notifications = stored.filter(n => n.timestamp > timeLimit);
        localStorage.setItem(NOTIFICATIONS_KEY, JSON.stringify(notifications));
    } catch (e) { notifications = [];}
    renderNotificationList();
    }

    function renderNotificationList() {
        const today = new Date().toISOString().split('T')[0];
        const notificationFooter = document.getElementById('notificationFooter');
        let urgentActivities = [];
        
        try {
            if (typeof backendActivities !== 'undefined') {
                const completedTasks = JSON.parse(localStorage.getItem(COMPLETED_TASKS_KEY) || '{}');
                urgentActivities = backendActivities.filter(a => {
                    if (completedTasks[a.id]) return false; // Ignore les tâches déjà accomplies
                    const actDate = a.start.split('T')[0];
                    // Ne garde que l'historique : les tâches en retard (passées) ou du jour
                    return actDate <= today && (a.type_name.includes('action') || a.type_name.includes('task') || a.type_name.includes('échéance'));
                });
                // Trie de la plus ancienne à la plus récente
                urgentActivities.sort((a, b) => a.start.localeCompare(b.start));
            }
        } catch(e) {}

        const totalNotifs = urgentActivities.length + notifications.length;
        
        if (totalNotifs === 0) {
            NotificationList.innerHTML = '<div class="notification-empty-state" style="color: #999; text-align:center; font-style: italic;">Aucune tâche en retard ou notification.</div>';
            notificationCountBadge.style.display = 'none'; // NOSONAR
            notificationBellIcon.classList.remove('ringing');
            if (notificationFooter) notificationFooter.style.display = 'none';
            return;
        }

        notificationCountBadge.innerText = totalNotifs;
        notificationCountBadge.style.display = 'block';
        notificationBellIcon.classList.add('ringing');
        NotificationList.innerHTML = '';
        if (notificationFooter) notificationFooter.style.display = 'block';

        // Affichage de l'historique des tâches urgentes
        urgentActivities.forEach(act => {
            const actDate = act.start.split('T')[0];
            const isOverdue = actDate < today;
            
            const bgColor = isOverdue ? '#fdedec' : '#fdf2e9';
            const borderColor = isOverdue ? '#c0392b' : '#f39c12';
            const titleColor = isOverdue ? '#c0392b' : '#d35400'; // NOSONAR
            const titleText = isOverdue ? '⚠️ En retard (' + actDate.split('-').reverse().join('/') + ')' : "🔔 À faire aujourd'hui";
            
            const notifItem = document.createElement('div');
            notifItem.className = 'notification-alert-item';
            notifItem.style.cssText = `display:flex; justify-content:space-between; align-items:center; background:${bgColor}; border-left:4px solid ${borderColor}; padding:8px 10px; border-radius:4px; font-size:0.9em; margin-bottom:8px; transition: background 0.2s;`;

            const textContainer = document.createElement('div');
            textContainer.style.flexGrow = '1';

            const titleDiv = document.createElement('div');
            titleDiv.style.cssText = `font-weight:bold; color:${titleColor};`;
            titleDiv.innerText = titleText;
            

            const descDiv = document.createElement('div');
            descDiv.className = 'notification-alert-desc';
            descDiv.style.cssText = `color:#333; margin-top:2px;`;
            descDiv.innerText = act.title;

            textContainer.appendChild(titleDiv);
            textContainer.appendChild(descDiv);

            const actionsContainer = document.createElement('div');
            actionsContainer.style.cssText = `display:flex; flex-direction:column; gap:5px; margin-left:10px;`;

            const viewBtn = document.createElement('button');
            viewBtn.innerHTML = 'Voir';
            viewBtn.style.cssText = `background:#2980b9; color:white; border:none; border-radius:4px; padding:4px 8px; cursor:pointer; font-size:0.8em; width:70px;`;
            viewBtn.addEventListener('click', (e) => {
                 e.stopPropagation();
                 notificationPanel.style.display = 'none';
                 window.showActivityDetails(act.id);
            });

            const completeBtn = document.createElement('button');
            completeBtn.innerHTML = 'Réalisé';
            completeBtn.style.cssText = `background:#27ae60; color:white; border:none; border-radius:4px; padding:4px 8px; cursor:pointer; font-size:0.8em; width:70px;`;

            completeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                toggleTaskCompletion(String(act.id), true);
                notifItem.style.transition = 'opacity 0.3s, transform 0.3s';
                notifItem.style.opacity = '0';
                notifItem.style.transform = 'translateX(20px)';
                setTimeout(() => { renderNotificationList(); renderTasksList(); }, 300);
                showToast('Tâche marquée comme accomplie !', 'success');
            });

            actionsContainer.appendChild(viewBtn);
            actionsContainer.appendChild(completeBtn);
            notifItem.appendChild(textContainer);
            notifItem.appendChild(actionsContainer);
            NotificationList.appendChild(notifItem);
        });

        // Affichage des notifications locales standards additionnelles
        notifications.forEach(notif => {
            const notifItem = document.createElement('div');
            notifItem.className = 'notification-alert-item';
            notifItem.style.cssText = `background:#f8f9fa; border-left:4px solid #2980b9; padding:8px 10px; border-radius:4px; font-size:0.9em; margin-bottom:8px;`;
            notifItem.innerText = notif.message || notif;
            NotificationList.appendChild(notifItem);
        });
    }

    if (clearNotificationBtn) {
        clearNotificationBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            notifications = [];
            localStorage.setItem(NOTIFICATIONS_KEY, JSON.stringify(notifications));
            renderNotificationList();
        });
    }

    // 1. Ecouteur d'événement sur la cloche pour ouvrir/fermer le panneau
    notificationBellIcon.addEventListener('click', function(event) {
        event.stopPropagation(); // Empêche la fermeture immédiate du panneau

        if(notificationPanel.style.display === 'none') {
            notificationPanel.style.display = 'flex'; 
        } else {
            notificationPanel.style.display ='none';
        }
    });

    // 2. Ecouteur d'événement sur tout le document pour ferme le panneau si on clique à coté
    document.addEventListener('click', function(event) {
        // Si le panneau est ouvert ET qu'on clique sur un élément qui n'est pas le panneau
        if (notificationPanel.style.display === 'flex' && !notificationPanel.contains(event.target)){
            notificationPanel.style.display = 'none';
        }
    });

    // --- Mode Sombre (Dark Mode) ---
    const darkModeToggle = document.getElementById('darkModeToggle');
    const isDarkMode = localStorage.getItem('creme_dark_mode') === 'true';

    if (isDarkMode) {
        document.body.classList.add('dark-mode');
        darkModeToggle.checked = true;
    }

    darkModeToggle.addEventListener('change', (e) => {
        document.body.classList.toggle('dark-mode', e.target.checked);
        localStorage.setItem('creme_dark_mode', e.target.checked);
    });

    // --- Salutation intelligente et dynamique ---
    const userName = "{{ user.first_name|default:user.username|title|escapejs }}";
    const currentHour = new Date().getHours();
    let greeting = "";

    if (currentHour >= 5 && currentHour < 12) { // NOSONAR
        greeting = `Bonjour ${userName}, prêt pour une nouvelle journée ?`;
    } else if (currentHour >= 12 && currentHour < 14) {
        greeting = `Bon appétit, ${userName} !`;
    } else if (currentHour >= 14 && currentHour < 18) {
        greeting = `Bon après-midi, ${userName} !`;
    } else {
        greeting = `Bonsoir ${userName}, belle fin de journée !`;
    }
    document.getElementById('dynamicGreeting').innerText = greeting;

    // --- Données des derniers contacts ---
    let latestContacts = [];
    try {
        // On suppose qu'une variable 'latest_contacts_json' est passée par la vue Django // NOSONAR
        latestContacts = JSON.parse("{{ latest_contacts_json|escapejs|default:'[]' }}");
    } catch(e) {
        console.error("Erreur de parsing des derniers contacts", e);
    }

    // --- Données pour les statistiques ---
    let homeStats = {}; // NOSONAR
    try {
        homeStats = JSON.parse("{{ home_stats_json|escapejs|default:'{}' }}");
    } catch(e) {
        console.error("Erreur de parsing des statistiques", e);
    }

    // --- Fonctionnalité Drag & Drop pour les widgets ---
    const homeGrid = document.querySelector('.home-grid');
    let draggedWidget = null;

    // Charger l'ordre sauvegardé
    const savedOrder = JSON.parse(localStorage.getItem('creme_widget_order') || '[]');
    if (savedOrder && savedOrder.length > 0) {
        savedOrder.forEach(widgetId => {
            const widget = document.getElementById(widgetId);
            if (widget) homeGrid.appendChild(widget);
        });
    }

    homeGrid.addEventListener('dragstart', function(e) {
        // On évite de lancer le glisser-déposer quand on clique dans un champ de texte ou sur un bouton interactif // NOSONAR
        if (['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON', 'A', 'SPAN'].includes(e.target.tagName) && !e.target.classList.contains('drag-handle')) {
            e.preventDefault(); // Annule le drag
            return;
        }
        const widget = e.target.closest('.draggable-widget');
        if (widget) {
            draggedWidget = widget;
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/plain', widget.id); // Requis pour Firefox
            setTimeout(() => widget.classList.add('dragging'), 0);
        }
    });

    homeGrid.addEventListener('dragend', function() {
        if (draggedWidget) {
            draggedWidget.classList.remove('dragging');
            draggedWidget = null;
            
            // Sauvegarder le nouvel ordre des widgets
            const currentOrder = Array.from(homeGrid.querySelectorAll('.draggable-widget')).map(w => w.id);
            localStorage.setItem('creme_widget_order', JSON.stringify(currentOrder));
        }
    });

    homeGrid.addEventListener('dragover', function(e) {
        e.preventDefault(); // Autorise le drop
        const targetWidget = e.target.closest('.draggable-widget');
        
        if (targetWidget && targetWidget !== draggedWidget && draggedWidget) {
            const rect = targetWidget.getBoundingClientRect();
            const relX = e.clientX - rect.left;
            
            // Si on survole la moitié droite du widget ciblé, on insère après, sinon avant // NOSONAR
            if (relX > rect.width / 2) {
                homeGrid.insertBefore(draggedWidget, targetWidget.nextSibling);
            } else {
                homeGrid.insertBefore(draggedWidget, targetWidget);
            }
        }
    });

    // Fonctionnalité Réduire/Agrandire (collapse) pour widgets
    const headers = document.querySelectorAll('.collapsible-header');

    // Restaurer l'état réduit depuis le localStorage au chargement
    const collapsedWidgets = JSON.parse(localStorage.getItem('creme_collapsed_widgets') || '[]');
    collapsedWidgets.forEach(widgetId => {
        const widget = document.getElementById(widgetId);
        if (widget) {
            widget.classList.add('widget-collapsed');
            const header = widget.querySelector('.collapsible-header');
            if (header) {
                widget.style.maxHeight = (header.offsetHeight + 40) + 'px';
            }
        }
    });

    headers.forEach(header => {
        header.addEventListener('click', function(e){
            //On empêche la réduction si on clique sur un bouton, menu déroulant, ou la poignée de drag // NOSONAR
            if (['BUTTON','SELECT','INPUT'].includes(e.target.tagName)|| e.target.classList.contains('drag-handle')) {
                return;
            }

            const widget = this.closest('.draggable-widget');
            if (widget) {
                const isCollapsed = widget.classList.contains('widget-collapsed');

                if (isCollapsed) {
                    // Action : Agrandir en douceur // NOSONAR
                    widget.classList.remove('widget-collapsed');
                    widget.style.maxHeight = widget.scrollHeight + 'px';
                    setTimeout(() => {
                        if (widget.classList.contains('widget-collapsed')) widget.style.maxHeight = 'none';
                    }, 400); // Fin de l'animation
                } else {
                    // Action : Réduire en douceur // NOSONAR
                    widget.style.maxHeight = widget.scrollHeight + 'px'; // Départ
                    widget.offsetHeight; // Force l'actualisation visuelle
                    widget.classList.add('widget-collapsed'); // NOSONAR
                    widget.style.maxHeight = (header.offsetHeight + 40) + 'px'; // Arrivé
                }

                // Mise à jour de la mémoire du navigateur (localStorage)
                let savedCollapsed = JSON.parse(localStorage.getItem('creme_collapsed_widgets') || '[]');
                if (widget.classList.contains('widget-collapsed')) {
                    if(!savedCollapsed.includes(widget.id)) savedCollapsed.push(widget.id);
                }else {
                    savedCollapsed = savedCollapsed.filter(id => id !== widget.id);
                }
                localStorage.setItem('creme_collapsed_widgets',JSON.stringify(savedCollapsed));
            }
        })
    });
    const calendarDays = document.getElementById('calendarDays');
    const calendarDates = document.getElementById('calendarDates');
    const calendarWeekView = document.getElementById('calendarWeekView');
    const calendarDayView = document.getElementById('calendarDayView');
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    const monthViewBtn = document.getElementById('monthViewBtn');
    const weekViewBtn = document.getElementById('weekViewBtn');
    const dayViewBtn = document.getElementById('dayViewBtn');
    const yearViewBtn = document.getElementById('yearViewBtn');
    const todayBtn = document.getElementById('todayBtn');
    
    
    let currentView = 'month';
    // Variables pour la modale // NOSONAR
    const eventModal = document.getElementById('eventModal');
    const modalTitle = document.getElementById('modalTitle');
    
    const modalListView = document.getElementById('modalListView');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const addDayActivityBtns = document.querySelectorAll('.addDayActivityBtn');

    const modalCreateView = document.getElementById('modalCreateView');
    const eventInput = document.getElementById('eventInput');
    const eventDraftStatus = document.getElementById('eventDraftStatus');
    const eventTime = document.getElementById('eventTime');
    const cancelCreateBtn = document.getElementById('cancelCreateBtn');
    const saveEventBtn = document.getElementById('saveEventBtn');
    const locationOptions = document.getElementById('locationOptions');
    const eventLocationRadios = document.querySelectorAll('input[name="eventLocation"]');
    const addressInputContainer = document.getElementById('addressInputContainer');
    const eventAddress = document.getElementById('eventAddress');
    
    // Variables pour la modale des tâches // NOSONAR
    const taskModal = document.getElementById('taskModal');
    const taskInputText = document.getElementById('taskInputText');
    const taskDraftStatus = document.getElementById('taskDraftStatus');
    const taskInputDate = document.getElementById('taskInputDate');
    const taskInputDueDate = document.getElementById('taskInputDueDate');
    const taskInputDueTime = document.getElementById('taskInputDueTime');
    const cancelTaskBtn = document.getElementById('cancelTaskBtn');
    const saveTaskBtn = document.getElementById('saveTaskBtn');

    const addTaskBtn = document.getElementById('addTaskBtn');
    const tasksList = document.getElementById('tasksList');
    const taskSearchInput = document.getElementById('taskSearchInput');

    // Nouveaux éléments pour la jauge // NOSONAR
    const taskProgressContainer = document.getElementById('taskProgressContainer');
    const taskProgressBar = document.getElementById('taskProgressBar');
    const taskProgressText = document.getElementById('taskProgressText');

    // --- Auto-save (Brouillons) ---
    let eventDraftTimeout;
    eventInput.addEventListener('input', function() {
        localStorage.setItem('creme_event_draft', this.value);
        eventDraftStatus.style.opacity = '1';
        clearTimeout(eventDraftTimeout);
        eventDraftTimeout = setTimeout(() => { eventDraftStatus.style.opacity = '0'; }, 2000);
    });

    let taskDraftTimeout;
    taskInputText.addEventListener('input', function() {
        localStorage.setItem('creme_task_draft', this.value);
        taskDraftStatus.style.opacity = '1';
        clearTimeout(taskDraftTimeout);
        taskDraftTimeout = setTimeout(() => { taskDraftStatus.style.opacity = '0'; }, 2000);
    });

    function updateTaskProgress() {
        const checkboxes = tasksList.querySelectorAll('input[type="checkbox"]');
        const total = checkboxes.length;

        if (total === 0) {
            if (taskProgressContainer) taskProgressContainer.style.display = 'none';
            if (taskProgressText) taskProgressText.style.display = 'none'; // NOSONAR
            return;
        }

        if (taskProgressContainer) taskProgressContainer.style.display = 'block';
        if (taskProgressText) taskProgressText.style.display = 'block'; // NOSONAR

        const checked = Array.from(checkboxes).filter(cb => cb.checked).length;
        const percentage = Math.round((checked / total) * 100);

        taskProgressBar.style.width = percentage + '%';
        taskProgressText.innerText = percentage + '% complété';
        
        if (percentage === 100) {
            taskProgressBar.style.backgroundColor = '#27ae60'; // Vert quand tout est fini
        } else {
            taskProgressBar.style.backgroundColor = '#2980b9'; // Bleu en cours
        }

        // Rafraîchir la cloche de notifications en temps réel
        if (typeof renderNotificationList === 'function') {
            renderNotificationList();
        }
    }

    // --- Filtre de recherche rapide pour les tâches ---
    function applyTaskFilter() {
        if (!taskSearchInput) return;
        const searchTerm = taskSearchInput.value.toLowerCase();
        const tasks = tasksList.querySelectorAll('.task-item');
        tasks.forEach(task => {
            const label = task.querySelector('label');
            if (label && label.innerText.toLowerCase().includes(searchTerm)) {
                task.style.display = 'flex';
            } else {
                task.style.display = 'none';
            }
        });
    }
    if (taskSearchInput) {
        taskSearchInput.addEventListener('input', applyTaskFilter);
    }

    let currentEventsDiv = null;
    let currentDayTitle = "";
    let currentCategory = "";
    let selectedDateStr = "";

    // Met à jour la liste affichée dans la modale
    function refreshModalList() {
        // Vider les listes
        document.querySelectorAll('.modal-event-list').forEach(list => list.innerHTML = "");
        const completedTaskIds = getCompletedTasks();

        if (currentEventsDiv) {
            const events = currentEventsDiv.querySelectorAll('.event-item');
            events.forEach(ev => {
                const cat = ev.getAttribute('data-category');
                const actId = ev.getAttribute('data-id');
                const list = document.getElementById('list-' + cat);
                if (list) {
                    const item = document.createElement('div');
                    item.classList.add('modal-event-item');
                    item.setAttribute('data-category', cat);

                    // Conteneur flexible pour aligner le texte à gauche et les boutons à droite
                    item.style.display = "flex";
                    item.style.justifyContent = "space-between";
                    item.style.alignItems = "center";

                    const leftDiv = document.createElement("div");
                    leftDiv.style.display = "flex";
                    leftDiv.style.alignItems = "center";
                    leftDiv.style.overflow = "hidden";

                    const checkbox = document.createElement("input");
                    checkbox.type = "checkbox";
                    checkbox.style.marginRight = "8px";
                    checkbox.style.cursor = "pointer";

                    const textSpan = document.createElement('label');
                    textSpan.innerText = ev.getAttribute("data-title") || ev.innerText;
                    textSpan.style.cursor = "pointer";

                    // On vérifie si la tâche est déja accomplie pour pré-cocher la case
                    if (actId && completedTaskIds.includes(String(actId))) {
                        checkbox.checked = true;
                        textSpan.style.textDecoration = "line-through";
                        textSpan.style.color = '#999';
                    } 

                    // On ajoute l'action à executer quand on coche/décoche la case
                    checkbox.addEventListener('change', function() {
                        if (actId) {
                            toggleTaskCompletion(String(actId), this.checked); // Sauvegarde l'état
                            if (this.checked) {
                                textSpan.style.textDecoration = 'line-through';
                                textSpan.style.color = '#999';
                                showToast("Activité accomplie !", "success");
                            } else {
                                textSpan.style.textDecoration = "none";
                                textSpan.style.color ="";
                                showToast("Activité marquée comme non accomplie", "error");
                            }
                            render(); //Rafraichit tout le calendrier
                            renderTasksList(); // Rafraichit la liste des tâches à droite
                            if(typeof renderNotificationList === 'function') renderNotificationList();

                        }
                    });
                    leftDiv.appendChild(checkbox);
                    leftDiv.appendChild(textSpan);
                    item.appendChild(leftDiv);

                    // Si l'événement a un ID (il provient de la base de données), on ajoute les boutons
                    if (actId && !String(actId).startsWith('local_')) {
                        const actionsDiv = document.createElement('div');
                        actionsDiv.style.display = "flex";
                        actionsDiv.style.gap = "10px"; // NOSONAR
                        
                        const contactId = ev.getAttribute('data-contact-id');
                        if (contactId) {
                            const contactBtn = document.createElement('a');
                            contactBtn.href = `{% url 'persons__view_contact' 999999 %}`.replace('999999', contactId);
                            contactBtn.innerHTML = "👤";
                            contactBtn.title = "Voir le contact";
                            contactBtn.style.textDecoration = "none";
                            actionsDiv.appendChild(contactBtn);
                        }

                        const viewBtn = document.createElement('a');
                        viewBtn.href = `{% url 'activities__view_activity' 999999 %}`.replace('999999', actId);
                        viewBtn.innerHTML = "Observer";
                        viewBtn.title = "Détails / Supprimer";
                        viewBtn.style.textDecoration = "none";

                        const editBtn = document.createElement('a');
                        editBtn.href = `{% url 'activities__edit_activity' 999999 %}`.replace('999999', actId);
                        editBtn.innerHTML = "Modifier";
                        editBtn.title = "Modifier";
                        editBtn.style.textDecoration = "none";

                        actionsDiv.appendChild(viewBtn);
                        actionsDiv.appendChild(editBtn);
                        item.appendChild(actionsDiv);
                    }
                    list.appendChild(item);
                }
            });
        }

        // Ajouter le message vide si la catégorie n'a pas d'événement
        document.querySelectorAll('.modal-event-list').forEach(list => {
            if (list.children.length === 0) {
                list.innerHTML = "<div class='empty-events-msg'>Aucun élément.</div>";
            }
        });
    }

    let currentDate = new Date();

    // On récupère les événements du CRM depuis le contexte Python
    let backendActivities = [];
    try {
        backendActivities = JSON.parse("{{ activities_json|escapejs|default:'[]' }}");
    } catch(e) {
        console.error("Erreur de parsing des activités", e);
    } 
    
    // --- Chargement des tâches et événements locaux depuis le navigateur ---
    let localActivities = [];
    try {
        localActivities = JSON.parse(localStorage.getItem('creme_local_activities') || '[]');
    } catch(e) {
        console.error("Erreur de parsing des activités locales", e);
    }
    backendActivities = backendActivities.concat(localActivities); // NOSONAR

    // Activer la cloche une fois les données chargées
    loadNotifications();

    function renderMonthView() {
        const completedTaskIds = getCompletedTasks();
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();
        const today = new Date();

        const monthNames = [
            "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",  // NOSONAR
            "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
        ];
        todayBtn.innerText = `${monthNames[month]} ${year}`;

        calendarDays.innerHTML = `
            <div>Lundi</div><div>Mardi</div><div>Mercredi</div><div>Jeudi</div><div>Vendredi</div><div>Samedi</div><div>Dimanche</div>
        `;
        calendarDays.style.gridTemplateColumns = 'repeat(7, 1fr)';

        calendarDates.innerHTML = "";

        const firstDay = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        const prevMonthDays = new Date(year, month, 0).getDate();

        // Ajustement pour que la semaine commence le lundi (0=Dimanche -> 6=Dimanche) // NOSONAR
        let startDay = firstDay === 0 ? 6 : firstDay - 1;

        // Jours du mois précédent
        for (let i = startDay; i > 0; i--) {
            const dayDiv = document.createElement("div");
            dayDiv.classList.add("calendar-day", "other-month");
            
            const dateSpan = document.createElement("span"); // NOSONAR
            dateSpan.classList.add("day-number");
            dateSpan.innerText = prevMonthDays - i + 1; // NOSONAR
            
            dayDiv.appendChild(dateSpan);
            calendarDates.appendChild(dayDiv);
        }

        // Jours du mois courant
        for (let i = 1; i <= daysInMonth; i++) {
            const dayDiv = document.createElement("div");
            dayDiv.classList.add("calendar-day");
            if (i === today.getDate() && month === today.getMonth() && year === today.getFullYear()) {
                dayDiv.classList.add("today");
            }

            const dateSpan = document.createElement("span"); // NOSONAR
            dateSpan.classList.add("day-number");
            dateSpan.innerText = i;
            dayDiv.appendChild(dateSpan);

            const eventsDiv = document.createElement("div");
            eventsDiv.classList.add("day-events");
            dayDiv.appendChild(eventsDiv);

            // --- Intégration des événements du CRM ---
            const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(i).padStart(2, '0')}`;
            const dayActivities = backendActivities.filter(a => a.start.startsWith(dateStr));
            
            dayActivities.forEach(act => {
                const eventItem = document.createElement("div");
                eventItem.classList.add("event-item");

                if (completedTaskIds.includes(String(act.id))) {
                    eventItem.classList.add("completed-event");
                }

                let cat = "evenements";
                if (act.type_name.includes("rendez-vous") || act.type_name.includes("meeting")) cat = "rendezvous";
                else if (act.type_name.includes("échéance") || act.type_name.includes("echeance")) cat = "echeances";
                else if (act.type_name.includes("action") || act.type_name.includes("task")) cat = "actions";
                
                eventItem.setAttribute("data-category", cat);
                eventItem.setAttribute("data-id", act.id); // On enregistre l'ID caché dans l'élément HTML
                if (act.contact_id) {
                    eventItem.setAttribute("data-contact-id", act.contact_id); // Sauvegarde l'ID du contact s'il y en a un
                }
                const timeStr = (act.time && act.time !== "00:00") ? act.time + " - " : "";
                const dueStr = act.due_date ? ` (Échéance: ${act.due_date.split('-').reverse().join('/')}${act.due_time ? ' à ' + act.due_time : ''})` : "";

                const titleText = act.contact_id ? timeStr + act.title + dueStr + " 👤" : timeStr + act.title + dueStr;
                eventItem.setAttribute("data-title", titleText);
                eventItem.title = titleText; // Affiche le titre au survol

                eventsDiv.appendChild(eventItem);
            }); // Fin forEach dayActivities
            // -----------------------------------------

            // Ouverture de la modale au clic sur le jour
            dayDiv.addEventListener('click', function() {
                currentEventsDiv = eventsDiv;
                currentDayTitle = `Événements du ${i} ${monthNames[month]} ${year}`;
                // Sauvegarde de la date (Format YYYY-MM-DD) pour pouvoir la passer à l'URL du CRM // NOSONAR
                selectedDateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(i).padStart(2, '0')}`;
                modalTitle.innerText = currentDayTitle;
                
                refreshModalList(); // NOSONAR
                
                modalListView.style.display = 'block';
                modalCreateView.style.display = 'none';
                eventModal.style.display = 'flex'; // Affiche la modale
            });

            calendarDates.appendChild(dayDiv);
        }
    }

    function renderWeekView() {
        const completedTaskIds = getCompletedTasks();
        const year = currentDate.getFullYear();
        const today = new Date();

        // 1. Calculer les dates de la semaine // NOSONAR
        const weekDates = [];
        const currentDayOfWeek = currentDate.getDay() === 0 ? 6 : currentDate.getDay() - 1; // 0=Lundi, 6=Dimanche
        const weekStart = new Date(currentDate);
        weekStart.setDate(currentDate.getDate() - currentDayOfWeek);

        for (let i = 0; i < 7; i++) {
            const date = new Date(weekStart);
            date.setDate(weekStart.getDate() + i);
            weekDates.push(date);
        }

        // 2. Mettre à jour les en-têtes // NOSONAR
        const startMonthName = weekDates[0].toLocaleString('fr-FR', { month: 'long' });
        const endMonthName = weekDates[6].toLocaleString('fr-FR', { month: 'long' });
        todayBtn.innerText = (startMonthName === endMonthName)
            ? `Du ${weekDates[0].getDate()} au ${weekDates[6].getDate()} ${startMonthName} ${year}`
            : `Du ${weekDates[0].getDate()} ${startMonthName} au ${weekDates[6].getDate()} ${endMonthName} ${year}`;

        calendarDays.innerHTML = `<div></div>`; // Vide pour la colonne des heures
        calendarDays.style.gridTemplateColumns = '50px repeat(7, 1fr)';
        weekDates.forEach(d => {
            const dayHeader = document.createElement('div');
            dayHeader.innerHTML = `${d.toLocaleString('fr-FR', { weekday: 'short' })} <span class="day-number">${d.getDate()}</span>`;
            if (d.toDateString() === today.toDateString()) {
                dayHeader.querySelector('.day-number').classList.add('today');
            }
            calendarDays.appendChild(dayHeader);
        });

        // 3. Construire la grille de la semaine // NOSONAR
        calendarWeekView.innerHTML = '';
        const weekGrid = document.createElement('div');
        weekGrid.className = 'week-grid-content';
        
        const timeCol = document.createElement('div');
        timeCol.className = 'week-time-col';
        
        const dayCols = [];
        for (let i = 0; i < 7; i++) {
            const dayCol = document.createElement('div');
            dayCol.className = 'week-day-col';
            dayCol.setAttribute('data-date', weekDates[i].toISOString().split('T')[0]);
            dayCols.push(dayCol);
        }

        for (let hour = 8; hour < 20; hour++) {
            const timeStr = `${String(hour).padStart(2, '0')}:00`;
            const timeSlot = document.createElement('div');
            timeSlot.className = 'week-hour-slot';
            timeSlot.setAttribute('data-time', timeStr);
            timeCol.appendChild(timeSlot);

            dayCols.forEach(col => {
                const slot = document.createElement('div');
                slot.className = 'week-hour-slot';
                slot.setAttribute('data-time', timeStr);
                col.appendChild(slot);
            });
        }

        weekGrid.appendChild(timeCol);
        dayCols.forEach(col => weekGrid.appendChild(col));
        calendarWeekView.appendChild(weekGrid);

        // 4. Placer les événements // NOSONAR
        const weekStartStr = weekDates[0].toISOString().split('T')[0];
        const weekEndStr = weekDates[6].toISOString().split('T')[0];
        const weekActivities = backendActivities.filter(a => a.start >= weekStartStr && a.start <= weekEndStr);

        const allDayCounts = {};

        weekActivities.forEach(act => {
            let topPosition = 0;
            const dateStr = act.start.split('T')[0];

            if (!act.time || act.time === "00:00") {
                allDayCounts[dateStr] = (allDayCounts[dateStr] || 0) + 1;
                topPosition = (allDayCounts[dateStr] - 1) * 28; // Empilement à partir du haut (8h00)
            } else {
                const [hour, minute] = act.time.split(':').map(Number);
                topPosition = ((Math.max(8, hour) - 8) * 50) + (minute / 60 * 50);
            }

            const eventItem = document.createElement('div');
            eventItem.className = 'week-event-item';

            if (completedTaskIds.includes(String(act.id))) {
                eventItem.classList.add("completed-event");
            }

            let cat = "evenements";
            if (act.type_name.includes("rendez-vous")) cat = "rendezvous";
            else if (act.type_name.includes("échéance")) cat = "echeances";
            else if (act.type_name.includes("action")) cat = "actions";
            
            eventItem.setAttribute("data-category", cat);
            eventItem.setAttribute("data-id", act.id);
            eventItem.style.top = `${topPosition}px`;
            const dueStr = act.due_date ? ` (Échéance: ${act.due_date.split('-').reverse().join('/')}${act.due_time ? ' à ' + act.due_time : ''})` : "";
            eventItem.innerText = act.title + dueStr;
            const timeLabel = (!act.time || act.time === "00:00") ? "Toute la journée" : act.time;
            eventItem.title = `${timeLabel} - ${act.title}${dueStr}`;

            eventItem.addEventListener('click', (e) => {
                e.stopPropagation();
                if (act.id && !String(act.id).startsWith('local_')) {
                    window.location.href = `{% url 'activities__view_activity' 999999 %}`.replace('999999', act.id);
                } else {
                    openDayModal(act.start.split('T')[0]);
                }
            });

            const targetCol = weekGrid.querySelector(`.week-day-col[data-date="${act.start.split('T')[0]}"]`);
            if (targetCol) targetCol.appendChild(eventItem);
        });

        // 5. Ajouter les gestionnaires de clics // NOSONAR
        function openDayModal(dateStr) {
            const dayActivities = backendActivities.filter(a => a.start.startsWith(dateStr));
            const tempEventsDiv = document.createElement('div');
            dayActivities.forEach(act => {
                const eventItem = document.createElement("div");
                let cat = "evenements";
                if (act.type_name.includes("rendez-vous")) cat = "rendezvous";
                else if (act.type_name.includes("échéance")) cat = "echeances";
                else if (act.type_name.includes("action")) cat = "actions";
                eventItem.setAttribute("data-category", cat);
                eventItem.setAttribute("data-id", act.id);
                if (act.contact_id) eventItem.setAttribute("data-contact-id", act.contact_id);
                const timeStr = (act.time && act.time !== "00:00") ? act.time + " - " : "";
                const dueStr = act.due_date ? ` (Échéance: ${act.due_date.split('-').reverse().join('/')}${act.due_time ? ' à ' + act.due_time : ''})` : "";
                eventItem.setAttribute("data-title", act.contact_id ? timeStr + act.title + dueStr + " 👤" : timeStr + act.title + dueStr);
                tempEventsDiv.appendChild(eventItem);
            });

            currentEventsDiv = tempEventsDiv;
            currentDayTitle = `Événements du ${new Date(dateStr+'T12:00:00').toLocaleDateString('fr-FR', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}`;
            selectedDateStr = dateStr;
            modalTitle.innerText = currentDayTitle;

            refreshModalList();
            modalListView.style.display = 'block';

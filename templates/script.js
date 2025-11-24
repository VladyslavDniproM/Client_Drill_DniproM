const chatContainer = document.getElementById("chat-container");
        const userInput = document.getElementById("user-input");
        const sendButton = document.getElementById("send-button");
        const statusElement = document.getElementById("status");
        const restartButton = document.getElementById("restart-button");
        const modelsContainer = document.getElementById("models-container");
        const modelsButtons = document.getElementById("modelsButtons"); // Оновлено, щоб використовувати overlay
        const modelsPrompt = document.getElementById("models-prompt");
        const progressHint = document.getElementById("progressHint");
        const questionProgressBar = document.getElementById("questionProgressBar");
        const modal = document.getElementById("rules-modal");
        const acceptBtn = document.getElementById("accept-rules-btn");
        const modelOverlay = document.getElementById("modelOverlay");
        const modelLeftArrow = document.getElementById("modelLeftArrow");
        const modelRightArrow = document.getElementById("modelRightArrow");

        // Події
        sendButton.addEventListener("click", sendMessage);
        userInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter") sendMessage();
        });
        restartButton.addEventListener("click", () => window.location.reload());

        modelLeftArrow.onclick = () => {
            modelsButtons.scrollBy({ left: -300, behavior: "smooth" });
        };

        modelRightArrow.onclick = () => {
            modelsButtons.scrollBy({ left: 300, behavior: "smooth" });
        };

        function blockChat() {
            userInput.disabled = true;
            sendButton.disabled = true;
        }

        function unblockChat() {
            userInput.disabled = false;
            sendButton.disabled = false;
            recordBtn.disabled = false;
        }

        acceptBtn.addEventListener("click", () => {
            modal.classList.add("hidden");
            setTimeout(() => {
                modal.style.display = "none";
                unblockChat();
                userInput.focus();
            }, 300);
            unblockChat();
            userInput.focus();
        });

        function addMessage(text, isUser) {
            const messageDiv = document.createElement("div");
            messageDiv.classList.add("message");
            messageDiv.classList.add(isUser ? "user-message" : "bot-message");
            messageDiv.textContent = text;
            chatContainer.appendChild(messageDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        function showTypingIndicator() {
            const typingDiv = document.createElement("div");
            typingDiv.classList.add("typing-indicator");
            typingDiv.id = "typing-indicator";
            typingDiv.innerHTML = `
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            `;
            chatContainer.appendChild(typingDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        function hideTypingIndicator() {
            const typingIndicator = document.getElementById("typing-indicator");
            if (typingIndicator) typingIndicator.remove();
        }

        function disableChat() {
            userInput.disabled = true;
            sendButton.disabled = true;
            recordBtn.disabled = true;
            hideModelButtons();
            statusElement.textContent = "Діалог завершено";
        }

        function showStageIndicator() {
          const h1 = document.getElementById('welcome-title');
          const indicator = document.getElementById('stage-indicator');

          h1.style.display = 'hidden';
          indicator.style.display = 'flex'; // або 'block' для вертикального вигляду
        }

function showModelHint() {
    const hintToast = document.getElementById("model-hint-modal");
    hintToast.classList.remove("hidden");
    hintToast.classList.add("success"); // Додаємо клас success для зеленого кольору
    
    // Автоматичне закриття через 15 секунд
    setTimeout(() => {
        hideModelHint();
    }, 15000);
}

function hideModelHint() {
    const hintToast = document.getElementById("model-hint-modal");
    hintToast.classList.add("hidden");
    hintToast.classList.remove("success"); // Видаляємо клас success
}

// Безпечне додавання обробників подій
document.addEventListener('DOMContentLoaded', function() {
    // Обробник для кнопки закриття в toast (якщо вона існує)
    const toastCloseBtn = document.querySelector('#model-hint-modal .feedback-toast-close');
    if (toastCloseBtn) {
        toastCloseBtn.addEventListener('click', hideModelHint);
    }
    
    // Обробник для кнопки "Зрозуміло" (якщо вона існує)
    const closeHintBtn = document.getElementById("close-hint-btn");
    if (closeHintBtn) {
        closeHintBtn.addEventListener("click", hideModelHint);
    }
    
    // Інші обробники
    const closeOverlayBtn = document.getElementById("close-model-overlay");
    if (closeOverlayBtn) {
        closeOverlayBtn.addEventListener("click", hideModelButtons);
    }
});

let modelHintShown = false;

        // Оновіть функцію updateProgressBar
function updateProgressBar(progress, maxQuestions = 5) {
    // Знаходимо елементи тільки якщо вони існують
    const questionProgressBar = document.getElementById("questionProgressBar");
    const progressHint = document.getElementById("progressHint");
    const progressContainer = document.getElementById("progressContainer");
    
    // Якщо елементи не знайдені - виходимо
    if (!questionProgressBar || !progressHint || !progressContainer) {
        return;
    }

    const percent = (Math.min(progress, maxQuestions) / maxQuestions) * 100;
    questionProgressBar.style.width = `${percent}%`;

    if (progress < maxQuestions) {
        progressHint.textContent = `Прогрес виявлення потреби`;
        progressHint.style.opacity = "1";
        progressContainer.style.opacity = "1";
        progressHint.style.display = "block";
        progressContainer.style.display = "block";

        // Показуємо кнопку "Оберіть модель" для ВСІХ категорій, але підказку тільки для не-exam
        if (progress >= 3 && !modelHintShown) {
            document.getElementById("choose-model-btn").style.display = "inline-block";
            
            // Показуємо підказку тільки для НЕ exam категорій
            if (selectedCategory !== "exam") {
                showModelHint();
            }
            modelHintShown = true;
        }
    } else {
        progressHint.textContent = "Максимальна кількість питань!";
        setTimeout(() => {
            progressHint.style.opacity = "0";
            progressContainer.style.opacity = "0";
        }, 1500);
        setTimeout(() => {
            progressHint.style.display = "none";
            progressContainer.style.display = "none";
        }, 2000);
    }
}

        function showModelButtons(models, promptText = "Оберіть модель:", attemptsLeft = 1) {
          modelsButtons.innerHTML = "";

          const modelData = {
              "CD-218Q": {
                  image: "/static/instruments/218Q.png",
                  specs: [
                      "24 Нм",
                      "Швидкоз'ємний патрон",
                      "Йде без акумулятора",
                      "Легкий та компактний",
                  ],
              },
              "CD-12QX": {
                  image: "/static/instruments/CD12QX.png",
                  specs: [
                      "25 Нм",
                      "Повний комплект",
                      "Для нескладних завдань",
                      "Повний комплект, в акції",
                  ],
              },
              "CD-201HBC": {
                  image: "/static/instruments/201HBC.png",
                  specs: [
                      "45 Нм",
                      "Безщітковий двигун",
                      "Для роботи навіть із цеглою",
                      "Йде без акумулятора",
                  ],
              },
              "CD-200BCULTRA": {
                  image: "/static/instruments/200BCULTRA.png",
                  specs: [
                      "60 Нм",
                      "Металевий патрон",
                      "Найсильніший шуруповерт",
                      "Йде без акумулятора",
                  ],
              },
              "CD-200BCCOMPACT": {
                  image: "/static/instruments/CD-200BCCOMPACT.png",
                  specs: [
                      "40 Нм",
                      "Металевий патрон",
                      "Найточніший шуруповерт",
                      "Йде без акумулятора",
                  ],
              },
              "CD-12CX": {
                  image: "/static/instruments/CD12CX.png",
                  specs: [
                      "30 Нм",
                      "Компактний та недорогий",
                      "Пластиковий патрон",
                      "Повний комлпект, в акції",
                  ],
              },
              "CD-12BC": {
                  image: "/static/instruments/CD-12BC.png",
                  specs: [
                      "40 Нм",
                      "Металевий патрон",
                      "Максимально компактний",
                      "Йде без акумулятора",
                  ],
              },
              "GS-140SE": {
                  image: "/static/instruments/gs140se.png",
                  specs: [
                      "1400 Вт",
                      "125 мм діаметр диску",
                      "Регулювання та підтримка обертів",
                      "Коротка ручка",
                  ],
              },
              "GL-160SE": {
                  image: "/static/instruments/gl160se.png",
                  specs: [
                      "1600 Вт",
                      "150 мм діаметр диску",
                      "Регулювання обертів та підтримка потужності",
                      "Довга ручка",
                  ],
              },
              "GS-98": {
                  image: "/static/instruments/gs98.png",
                  specs: [
                      "980 Вт",
                      "125 мм діаметр диску",
                      "Найдешевша та найпопулярніша КШМ",
                      "Коротка ручка",
                  ],
              },
              "GS-100S": {
                  image: "/static/instruments/gs100s.png",
                  specs: [
                      "1000 Вт",
                      "125 мм діаметр диску",
                      "Компактна КШМ із регулятором обертів",
                      "Коротка ручка",
                  ],
              },
              "GL-145S": {
                  image: "/static/instruments/GL145S.png",
                  specs: [
                      "1450 Вт",
                      "125 мм діаметр диску",
                      "Для робіт підвищеної складності",
                      "Довга ручка та регулятор обертів",
                  ],
              },
              "GS-120S": {
                  image: "/static/instruments/GS120S.png",
                  specs: [
                      "1200 Вт",
                      "125 мм діаметр диску",
                      "Плавний пуск та захист від повторного вмикання",
                      "Коротка ручка та регулятор обертів",
                  ],
              },
              "GL-240": {
                  image: "/static/instruments/GL240.png",
                  specs: [
                      "2400 Вт",
                      "230 мм діаметр диску",
                      "Для різу найтовстіших матеріалів",
                      "Поворотна довга ручка",
                  ],
              },
              "CG-12BC": {
                  image: "/static/instruments/cg12bc.png",
                  specs: [
                      "76 мм діаметр диску",
                      "12V болгарка",
                      "Максимально компактна",
                      "Має плавний пуск та захист від випадкового ввімкнення",
                  ],
              },
              "GL-125S": {
                  image: "/static/instruments/gl125s.png",
                  specs: [
                      "125 мм діаметр диску",
                      "1250 Вт",
                      "Проста та дешева КШМ",
                      "Довга ручка",
                  ],
              },
              "GL-190S": {
                  image: "/static/instruments/gl190s.png",
                  specs: [
                      "180 мм діаметр диску",
                      "1900 Вт потужності",
                      "Модель із плавним пуском та захистами",
                      "Модель для розрізання товстих матеріалів",
                  ],
              },
              "DGA-201BC": {
                  image: "/static/instruments/dga201BC.png",
                  specs: [
                      "125 мм діаметр диску",
                      "20V модель КШМ",
                      "Найкраща акумуляторна модель КШМ",
                      "Усі функції захистів та підтримка обертів",
                  ],
              },
              "DGA-202SBC": {
                  image: "/static/instruments/dga202sbc.png",
                  specs: [
                      "125 мм діаметр диску",
                      "20V модель КШМ",
                      "Єдина модель із повноцінним регулятором обертів",
                      "Має підтримку потужності",
                  ],
              },
              "DHR-200": {
                  image: "/static/instruments/DHR200.png",
                  specs: [
                      "20V перфоратор",
                      "1.5 Дж сила удару",
                      "Найслабший та найкомпактніший",
                      "Не має режиму руйнування",
                  ],
              },
              "DHR-201BC": {
                  image: "/static/instruments/DHR201BC.png",
                  specs: [
                      "20V перфоратор",
                      "1.7 Дж сила удару",
                      "Має безщітковий двигун",
                      "Має режим руйнування (удару)",
                  ],
              },
              "DHR-202BC": {
                  image: "/static/instruments/DHR202BC.png",
                  specs: [
                      "20V перфоратор",
                      "2.5 Дж сила удару",
                      "Бочковий, з безщітковим двигуном",
                      "Антивібраційна ручка",
                  ],
              },
              "RH-100": {
                  image: "/static/instruments/RH100.png",
                  specs: [
                      "Прямий перфоратор",
                      "2.6 Дж сила удару",
                      "Дешевий та надійний",
                      "Йде в кейсі",
                  ],
              },
              "RH-12Q": {
                  image: "/static/instruments/RH12Q.png",
                  specs: [
                      "Прямий перфоратор",
                      "2.8 Дж сила удару",
                      "Додатковий патрон для роботи з свердлами",
                      "Йде в кейсі",
                  ],
              },
              "RH-16": {
                  image: "/static/instruments/RH16.png",
                  specs: [
                      "Найсильніший прямий перфоратор",
                      "3.4 Дж сила удару",
                      "Вибір професіоналів",
                      "Йде в кейсі",
                  ],
              },
              "BH-14S": {
                  image: "/static/instruments/BH14S.png",
                  specs: [
                      "Універсальний бочковий перфоратор",
                      "4 Дж сила удару",
                      "Антивібраційна система",
                      "Окремий регулятор обертів",
                  ],
              },
              "BH-20": {
                  image: "/static/instruments/BH20.png",
                  specs: [
                      "Бочковий перфоратор",
                      "5.5 Дж сила удару",
                      "Вибір професіоналів",
                      "Індикації мережі та зносу",
                  ],
              },
              "BH-30": {
                  image: "/static/instruments/BH30.png",
                  specs: [
                      "Найбільший бочковий перфоратор",
                      "9 Дж сила удару",
                      "Збільшений патрон SDSMAX",
                      "Виключно для професійних завдань",
                  ],
              },
              "SAB-14DMINI": {
                  image: "/static/instruments/SAB14DMINI.png",
                  specs: [
                      "Найменший зварювальний інвертор",
                      "Має функцію HOT START",
                      "В комплекті йдуть зварювальні кабелі",
                      "Може працювати електродом 4 мм",
                  ],
              },
                "SAB-15DX": {
                  image: "/static/instruments/SAB15DX.png",
                  specs: [
                      "Універсальний інвертор",
                      "Має усі функції для зручності зварювання",
                      "Працює в режимі TIG-LIFT",
                      "В комплекті йдуть зварювальні кабелі",
                  ],
              },
                "M-16PW": {
                  image: "/static/instruments/M16PW.png",
                  specs: [
                      "Найбільш захищений інвертор",
                      "Може працювати від 140 Вольт напруги",
                      "Синій яскравий дисплей",
                      "Працює електродами до 4 мм",
                  ],
              },
                "SAB-17DX": {
                  image: "/static/instruments/SAB17DX.png",
                  specs: [
                      "Професійний інвертор",
                      "Має усі функції для зручності зварювання",
                      "Працює в режимі TIG-LIFT",
                      "Працює електродами до 5 мм",
                  ],
              },
                "M-20D": {
                  image: "/static/instruments/M20D.png",
                  specs: [
                      "Найпотужніший інвертор",
                      "Широкий дисплей із зручним керуванням",
                      "В комплекті йдуть зварювальні кабелі",
                      "Зварює метали товщиною більше 10 мм",
                  ],
              },
                  "DSG-25H": {
                  image: "/static/instruments/25H.png",
                  specs: [
                      "Найменша бензопила",
                      "Підійде для розпилу до 25 см деревини",
                      "Швидкий та зручний запуск",
                      "Споживає 500 мл/год палива",
                  ],
              },
                  "NSG-45H": {
                  image: "/static/instruments/45H.png",
                  specs: [
                      "Найпопулярніша бензопила",
                      "Підійде для розпилу до 40 см деревини",
                      "Швидкий та зручний запуск",
                      "Споживає 1400 мл/год палива",
                  ],
              },
                  "NSG-52H": {
                  image: "/static/instruments/52H.png",
                  specs: [
                      "Покращена бензопила",
                      "Підійде для розпилу до 45 см деревини",
                      "Швидкий та зручний запуск",
                      "Споживає 1800 мл/год палива",
                  ],
              },
                  "NSG-62H": {
                  image: "/static/instruments/62H.png",
                  specs: [
                      "Найбільша бензопила",
                      "Підійде для розпилу до 45 см деревини",
                      "Швидкий та зручний запуск",
                      "Споживає 2100 мл/год палива",
                  ],
              },
                  "DSE-15T": {
                  image: "/static/instruments/15T.png",
                  specs: [
                      "Найменша електропила",
                      "Підійде для розпилу до 30 см деревини",
                      "Аварійне гальмо та миттєва зупинка ланцюга",
                      "Зручна та мобільна",
                  ],
              },
                  "DSE-22S": {
                  image: "/static/instruments/22S.png",
                  specs: [
                      "Середня електропила",
                      "Підійде для розпилу до 35 см деревини",
                      "Аварійне гальмо, плавний пуск та миттєва зупинка ланцюга",
                      "Чудова для вертикального розпилу",
                  ],
              },
                  "DSE-24DS": {
                  image: "/static/instruments/24DS.png",
                  specs: [
                      "Найпотужніша електропила",
                      "Підійде для розпилу до 35 см деревини",
                      "Аварійне гальмо, плавний пуск та миттєва зупинка ланцюга",
                      "Чудова для розпилу під різними кутами",
                  ],
              },
                  "DCS-201BCDUAL": {
                  image: "/static/instruments/201BCDUAL.png",
                  specs: [
                      "Професійна 40V акумуляторна пила",
                      "Підійде для розпилу до 35 см деревини",
                      "Безщітковий двигун та захисти",
                      "Працює від двох акумуляторів",
                  ],
              },
                  "CS-12": {
                  image: "/static/instruments/CS12.png",
                  specs: [
                      "Найменша 12V пила-гілкоріз",
                      "Працює з гілками до 10 мм в діаметрі",
                      "Безключова система натягу ланцюга",
                      "Має захист від перенавантаження",
                  ],
              },
                  "DMS-201BC": {
                  image: "/static/instruments/DMS201BC.png",
                  specs: [
                      "Найменша 20V пила-гілкоріз",
                      "Працює з гілками до 15 мм в діаметрі",
                      "Безключова система натягу ланцюга",
                      "Має захист від перенавантаження",
                  ],
              },
                  "DNIPRO-M-43": {
                  image: "/static/instruments/M43.png",
                  specs: [
                      "Найпопулярніша мотокоса",
                      "Ідеальний для 15 соток",
                      "Повна комплектація для початку роботи",
                      "Працює ножами 40Т та струною до 4.5 мм",
                  ],
              },
                  "33M": {
                  image: "/static/instruments/33M.png",
                  specs: [
                      "Мультиінструмент",
                      "Ідеальний для 5-10 соток",
                      "Кущоріз-висоторіз в комплекті",
                      "Працює ножами 40Т та струною до 3 мм",
                  ],
              },
                  "DNIPRO-M-110": {
                  image: "/static/instruments/110.png",
                  specs: [
                      "Зручна та легка",
                      "Ідеальний для 5 соток",
                      "Захист від перегріву та плавний пуск",
                      "Працює ножами 3Т та струною до 2.4 мм",
                  ],
              },
                  "DNIPRO-M-150S": {
                  image: "/static/instruments/150S.png",
                  specs: [
                      "Зручна та легка",
                      "Ідеальний для 5 соток",
                      "Захист від перегріву та плавний пуск",
                      "Працює ножами 3Т та струною до 2.4 мм",
                  ],
              },
                  "30L": {
                  image: "/static/instruments/30L.png",
                  specs: [
                      "Найлегший тример, 300 Вт",
                      "Ідеальний для 2 соток",
                      "Розбірна 3-х секційна штанга",
                      "Працює струною до 1.6 мм",
                  ],
              },
                  "DTC-200BCDUAL": {
                  image: "/static/instruments/200BCDUAL.png",
                  specs: [
                      "Професійний 40V акумуляторний тример",
                      "Підійде для косіння до 5 соток",
                      "Безщітковий двигун та захисти",
                      "Працює від двох акумуляторів",
                  ],
              },
                  "DTC-201": {
                  image: "/static/instruments/DTC201.png",
                  specs: [
                      "Максимально мобільний тример",
                      "Підійде для косіння до 2 соток",
                      "Телескопічна та поворотна штанга",
                      "Працює струною та пластиковими ножами",
                  ],
              },
                  "5-H": {
                  image: "/static/instruments/5H.png",
                  specs: [
                      "Зручний 5 л обприскувач",
                      "Літій-іонний акумулятор",
                      "Для обробки до 4 соток",
                      "до 150 хв безперервної роботи",
                  ],
              },
                  "12S": {
                  image: "/static/instruments/12S.png",
                  specs: [
                      "Середній 12 л обприскувач",
                      "Свинцево-кислотний акумулятор",
                      "Для обробки до 7 соток",
                      "до 4 годин безперервної роботи",
                  ],
              },
                  "16S": {
                  image: "/static/instruments/16S.png",
                  specs: [
                      "Найбільший 16 л обприскувач",
                      "Свинцево-кислотний акумулятор",
                      "Для обробки до 9 соток",
                      "до 4 годин безперервної роботи",
                  ],
              },
              "JS-8": {
                image: "/static/instruments/JS-8.png",
                specs: [
                  "Ємність: 8000 мА·г (PowerBank 4500 мА·г)",
                  "Пусковий струм: 400 А",
                  "Піковий струм: 800 А",
                  "Для двигунів до 4.0 л (бензин) / 2.5 л (дизель)",
                  "Функція PowerBank, LED-ліхтарик",
                  "Компактний та легкий"
                ]
              },
              "JS-12P": {
                image: "/static/instruments/JS-12P.png",
                specs: [
                  "Ємність: 12000 мА·г (PowerBank 6400 мА·г)",
                  "Пусковий струм: 600 А",
                  "Піковий струм: 1200 А",
                  "Підходить для двигунів до 8.0 л (бензин) / 6.5 л (дизель)",
                  "Працює як PowerBank, підтримка бездротової зарядки",
                  "Вбудований ліхтарик"
                ]
              },
              "JS-16": {
                image: "/static/instruments/JS-16.png",
                specs: [
                  "Ємність: 16000 мА·г (PowerBank 9500 мА·г)",
                  "Пусковий струм: 1000 А",
                  "Піковий струм: 2000 А",
                  "Для двигунів до 9.0 л (бензин) / 7.0 л (дизель)",
                  "Працює як PowerBank, LED-ліхтарик",
                  "Системи захисту від перенапруги, перегріву, короткого замикання"
                ]
              },
              "JS-16C": {
                image: "/static/instruments/JS-16C.png",
                specs: [
                  "Ємність: 16000 мА·г (PowerBank 9000 мА·г)",
                  "Пусковий струм: 1000 А",
                  "Піковий струм: 2000 А",
                  "Для двигунів до 9.0 л (бензин) / 7.0 л (дизель)",
                  "Вбудований компресор: накачування колеса R16 за 4 хв",
                  "PowerBank, ліхтарик, повний набір захистів"
                ]
              },
              "JS-70": {
                image: "/static/instruments/JS-70.png",
                specs: [
                  "Пусковий струм: 600 А",
                  "Зарядний струм: 7–55 А",
                  "Діапазон ємності АКБ: 70–550 А·год",
                  "Працює з АКБ 6/12/24 В",
                  "Режими: десульфатація, перевірка генератора, підтримка бортової мережі",
                  "Сумісність з гелевими, AGM, свинцево-кислотними акумуляторами",
                  "Великий дисплей для зручного керування"
                ]
              },
              "JS-80": {
                image: "/static/instruments/JS-80.png",
                specs: [
                  "Пусковий струм: 500 А (макс. 750 А)",
                  "Зарядний струм: 80–120 А",
                  "Діапазон ємності АКБ: 80–1200 А·год",
                  "Працює з АКБ 12/24 В",
                  "Призначений для великої техніки (тягачі, с/г техніка)",
                  "Кнопка дистанційного запуску для одного оператора",
                  "Захист від перевантаження, перегріву та неправильної полярності"
                ]
              },
              "BC-4I": {
                image: "/static/instruments/BC-4I.png",
                specs: [
                  "Автоматичний імпульсний зарядний пристрій",
                  "Напруга: 6/12 В",
                  "Ємність АКБ: 4–120 А·год",
                  "Струм заряджання: до 4 А",
                  "9-етапний процес заряджання",
                  "Режими: RECOND (відновлення), SUPPLY (джерело живлення)",
                  "Повний набір захистів: КЗ, зворотна полярність, перегрів, перезаряд"
                ]
              },
              "BC-10I": {
                image: "/static/instruments/BC-10I.png",
                specs: [
                  "Автоматичний імпульсний зарядний пристрій",
                  "Напруга: 6/12/24 В",
                  "Ємність АКБ: 4–280 А·год",
                  "Струм заряджання: до 10 А",
                  "9-етапний процес заряджання",
                  "Режими: RECOND (відновлення), SUPPLY (джерело живлення)",
                  "Захист від КЗ, перезаряду, неправильної полярності, перегріву"
                ]
              },
              "BC-25I": {
                image: "/static/instruments/BC-25I.png",
                specs: [
                  "Професійний імпульсний зарядний пристрій",
                  "Напруга: 12/24 В",
                  "Ємність АКБ: до 500 А·год",
                  "Струм заряджання: до 25 А",
                  "Режим Boost (пусковий, 12В 40А)",
                  "Режим десульфатації та перевірки генератора",
                  "LED-дисплей з діагностикою та індикацією помилок"
                ]
              },
              "AC-20": {
              image: "/static/instruments/AC-20.png",
              specs: [
                "Масляний компресор з прямим приводом",
                "Об'єм ресивера: 20 л",
                "Продуктивність: 140 л/хв (вхід), 101 л/хв (вихід)",
                "Потужність: 1100 Вт, 1 поршень",
                "Робочий тиск: 8 Бар",
                "Захист від перегріву та перекачування",
                "Компактний і зручний для гаража та дому"
              ]
            },
            "AC-48": {
              image: "/static/instruments/AC-48.png",
              specs: [
                "Масляний компресор з прямим приводом",
                "Об'єм ресивера: 48 л",
                "Продуктивність: 180 л/хв (вхід), 125 л/хв (вихід)",
                "Потужність: 1200 Вт, 1 поршень",
                "Робочий тиск: 8 Бар",
                "Система автоматичного ввімкнення/вимкнення (5–8 Бар)",
                "Легкий запуск при 5°C, зручне транспортування"
              ]
            },
            "AC-50LX": {
              image: "/static/instruments/AC-50LX.png",
              specs: [
                "Масляний компресор з прямим приводом",
                "Об'єм ресивера: 50 л",
                "Продуктивність: 190 л/хв (вхід), 135 л/хв (вихід)",
                "Потужність: 1500 Вт, 1 поршень",
                "Робочий тиск: 8 Бар",
                "Два швидкоз’ємних роз’єми + можливість підключення додаткового ресивера",
                "Колеса для зручного переміщення, кабель 4 м"
              ]
            },
            "AC-50V": {
              image: "/static/instruments/AC-50V.png",
              specs: [
                "Масляний компресор з прямим приводом, 2 поршні",
                "Об'єм ресивера: 50 л",
                "Продуктивність: 420 л/хв (вхід), 292 л/хв (вихід)",
                "Потужність: 2200 Вт",
                "Робочий тиск: 8 Бар",
                "Оптимальний для професійних робіт, фарбування, роботи з плазморізом",
                "Два виходи: швидкоз’ємний та звичайний штуцери"
              ]
            },
            "AC-50VG": {
              image: "/static/instruments/AC-50VG.png",
              specs: [
                "Масляний компресор з ремінним приводом",
                "Об'єм ресивера: 50 л",
                "Продуктивність: 400 л/хв (вхід), 290 л/хв (вихід)",
                "Потужність: 2200 Вт, 2 поршні",
                "Робочий тиск: 8 Бар",
                "Призначений для СТО, малярних і пневматичних робіт",
                "Знижене навантаження на двигун, підвищений моторесурс"
              ]
            },
            "AC-100VG": {
              image: "/static/instruments/AC-100VG.png",
              specs: [
                "Масляний компресор з ремінним приводом",
                "Об'єм ресивера: 100 л",
                "Продуктивність: 400 л/хв (вхід), 290 л/хв (вихід)",
                "Потужність: 2200 Вт, 2 поршні",
                "Робочий тиск: 8 Бар",
                "Для роботи з кількома пневмоінструментами та тривалих завдань",
                "Збільшені колеса, кабель 4 м, два швидкоз’ємних роз’єми"
              ]
            },
            "AC-9NL": {
              image: "/static/instruments/AC-9NL.png",
              specs: [
                "Безмасляний компресор",
                "Об'єм ресивера: 9 л",
                "Продуктивність: 110 л/хв (вхід), 85 л/хв (вихід)",
                "Потужність: 550 Вт",
                "Робочий тиск: 8 Бар",
                "Компактний та легкий, низький рівень шуму (≈60 дБ)",
                "Чисте повітря без масляних частинок, підходить для харчової та медичної сфери"
              ]
            },
            "AC-24NL": {
              image: "/static/instruments/AC-24NL.png",
              specs: [
                "Безмасляний компресор",
                "Об'єм ресивера: 24 л",
                "Продуктивність: 220 л/хв (вхід), 150 л/хв (вихід)",
                "Потужність: 1200 Вт",
                "Робочий тиск: 8 Бар",
                "Низький рівень шуму (≈80 дБ), система Sound-smooth",
                "Максимально чисте повітря, підходить для медичної та харчової промисловості"
              ]
            },
            "AC-50NL": {
              image: "/static/instruments/AC-50NL.png",
              specs: [
                "Безмасляний компресор з двома блоками",
                "Об'єм ресивера: 50 л",
                "Продуктивність: 350 л/хв (вхід), 240 л/хв (вихід)",
                "Потужність: 2200 Вт",
                "Робочий тиск: 8 Бар",
                "Система охолодження з 4 крильчатками, електромагнітний клапан",
                "Тиха робота, чисте повітря, оптимальний для СТО та столярних робіт"
              ]
            },
            "DTD-200": {
                image: "/static/instruments/DTD-200.png",
                specs: [
                  "Акумуляторний гвинтоверт",
                  "Крутний момент: 180 Нм",
                  "Об/хв: 0–2200",
                  "Уд/хв: 0–3000",
                  "Двигун: колекторний",
                  "Патрон: ¼’’ HEX",
                  "Компактний, підходить для нескладних завдань"
                ]
              },
              "DTD-201BCULTRA": {
                image: "/static/instruments/DTD-201BCULTRA.png",
                specs: [
                  "Акумуляторний гвинтоверт",
                  "Крутний момент: 230 Нм",
                  "Об/хв: 0–2900",
                  "Уд/хв: 0–4000",
                  "Двигун: безщітковий",
                  "Патрон: ¼’’ HEX",
                  "3 режими + R-режим для зриву кріплень"
                ]
              },
              "TD-12": {
                image: "/static/instruments/TD-12.png",
                specs: [
                  "Акумуляторний гвинтоверт 12В",
                  "Крутний момент: 140 Нм",
                  "Двигун: безщітковий",
                  "Патрон: ¼’’ HEX",
                  "Компактний і легкий",
                  "Оптимальний для монтажників та покрівельників"
                ]
              },
              "DTW-201BC": {
                image: "/static/instruments/DTW-201BC.png",
                specs: [
                  "Акумуляторний гайковерт",
                  "Крутний момент: до 350 Нм",
                  "2 швидкості (115 / 350 Нм)",
                  "Об/хв: 1900–2600",
                  "Уд/хв: 3000–3500",
                  "Двигун: безщітковий",
                  "Патрон: ½’’ квадрат",
                  "Компактний для роботи у важкодоступних місцях"
                ]
              },
              "DTW-202BC": {
                image: "/static/instruments/DTW-202BC.png",
                specs: [
                  "Акумуляторний гайковерт",
                  "Крутний момент: до 600 Нм",
                  "3 швидкості (300 / 400 / 600 Нм)",
                  "Об/хв: 1400–2400",
                  "Уд/хв: 1500–2200",
                  "Двигун: безщітковий",
                  "Патрон: ½’’ квадрат",
                  "Режим зриву гайки",
                  "Для роботи з великими кріпленнями, ідеально для СТО"
                ]
              },
              "PW-14B": {
                image: "/static/instruments/PW-14B.png",
                specs: [
                  "Мийка високого тиску",
                  "Потужність: 1800 Вт",
                  "Максимальний тиск: 140 Бар",
                  "Продуктивність: 390 л/год",
                  "Довжина шлангу: 8 м",
                  "Двигун: колекторний",
                  "Легка та мобільна для домашнього використання"
                ]
              },
              "PW-16BR": {
                image: "/static/instruments/PW-16BR.png",
                specs: [
                  "Мийка високого тиску",
                  "Потужність: 2000 Вт",
                  "Максимальний тиск: 160 Бар",
                  "Продуктивність: 450 л/год",
                  "Довжина шлангу: 8 м",
                  "Двигун: колекторний",
                  "Металева насадка з 6 форсунками для різних режимів"
                ]
              },
              "PW-18Ri": {
                image: "/static/instruments/PW-18Ri.png",
                specs: [
                  "Мийка високого тиску",
                  "Потужність: 3000 Вт",
                  "Максимальний тиск: 180 Бар",
                  "Продуктивність: 520 л/год",
                  "Довжина шлангу: 12 м",
                  "Двигун: асинхронний (безщітковий)",
                  "Розрахована на тривале використання, площі до 450 м²"
                ]
              },
              "LL-12": {
                image: "/static/instruments/LL-12.png",
                specs: [
                  "Акумуляторний ліхтар",
                  "Потужність світлового потоку: 1200 Лм",
                  "Дальність освітлення: до 300 м",
                  "Кут розсіювання: 25°",
                  "Час роботи: до 4 год",
                  "Зручна ручка, можливість кріплення на штатив"
                ]
              },
              "LL-12ULTRA": {
                image: "/static/instruments/LL-12ULTRA.png",
                specs: [
                  "Акумуляторний ліхтар",
                  "Потужність світлового потоку: 2000 Лм",
                  "Дальність освітлення: до 400 м",
                  "Кут розсіювання: 20°",
                  "Час роботи: до 6 год",
                  "Посилений корпус, захист від пилу та вологи IP54"
                ]
              },
              "DCL-200": {
                image: "/static/instruments/DCL-200.png",
                specs: [
                  "Акумуляторний ліхтар-прожектор",
                  "Потужність світлового потоку: 2000 Лм",
                  "3 режими яскравості",
                  "Час роботи: до 5 год",
                  "Регулювання кута нахилу",
                  "Компактний корпус для зручного перенесення"
                ]
              },
              "DCL-201": {
                image: "/static/instruments/DCL-201.png",
                specs: [
                  "Акумуляторний ліхтар-прожектор",
                  "Потужність світлового потоку: 3000 Лм",
                  "Регульований кут освітлення",
                  "Час роботи: до 6 год",
                  "Кріплення на гак або штатив",
                  "Вбудований захист від перегріву"
                ]
              },
              "FX-5": {
                image: "/static/instruments/FX-5.png",
                specs: [
                  "Акумуляторний ліхтар-фонарь",
                  "Потужність світлового потоку: 500 Лм",
                  "Дальність освітлення: до 150 м",
                  "Час роботи: до 10 год",
                  "Компактний корпус",
                  "Ідеальний для щоденного використання"
                ]
              },
              "FX-20": {
                image: "/static/instruments/FX-20.png",
                specs: [
                  "Акумуляторний ліхтар-фонарь",
                  "Потужність світлового потоку: 2000 Лм",
                  "Дальність освітлення: до 350 м",
                  "Час роботи: до 8 год",
                  "Ударостійкий корпус",
                  "Захист від вологи IP54"
                ]
              },
              "CFL-36M": {
                image: "/static/instruments/CFL-36M.png",
                specs: [
                  "Акумуляторний ліхтар-прожектор",
                  "Потужність світлового потоку: 3600 Лм",
                  "Кут розсіювання: 120°",
                  "Час роботи: до 7 год",
                  "Регульована підставка",
                  "Ідеальний для будівництва та ремонтних робіт"
                ]
              },
              "DCL-360": {
                image: "/static/instruments/DCL-360.png",
                specs: [
                  "Акумуляторний ліхтар-прожектор",
                  "Потужність світлового потоку: 3600 Лм",
                  "Кут освітлення: 360°",
                  "Час роботи: до 8 год",
                  "Можливість встановлення на штатив",
                  "Захист від пилу та вологи IP54"
                ]
              },
              "IL-36": {
                image: "/static/instruments/IL-36.png",
                specs: [
                  "Акумуляторний ліхтар",
                  "Потужність світлового потоку: 1600 Лм",
                  "Час роботи: до 5 год",
                  "Можливість підвішування",
                  "Регульований кут нахилу",
                  "Захищений корпус для роботи у важких умовах"
                ]
              },
              "ULTRA-150": {
                image: "/static/instruments/ULTRA-150.png",
                specs: [
                  "150 предметів у комплекті",
                  "Магнітні свічкові головки",
                  "Посилений ударний кардан ½",
                  "Біти типу 'M' для авто VAG-групи",
                  "Гарантія 5 років"
                ]
              },
              "ULTRA-SUPERLOCK-12": {
                image: "/static/instruments/ULTRA-SUPERLOCK-12.png",
                specs: [
                  "12 предметів у комплекті",
                  "Торцеві головки Super Lock",
                  "Для мопедів, мотоциклів, велосипедів",
                  "Тріскачка з квадратом ½",
                  "Подовжувач 125 мм"
                ]
              },
              "ULTRA-73": {
                image: "/static/instruments/ULTRA-73.png",
                specs: [
                  "73 предмети у комплекті",
                  "Для легкових авто та автобусів",
                  "Тріскачки ½ та ¼",
                  "Свічкові торцеві головки",
                  "Торцеві головки Super Lock"
                ]
              },
              "ULTRA-56": {
                image: "/static/instruments/ULTRA-56.png",
                specs: [
                  "56 предметів у комплекті",
                  "Ключі рожково-накидні",
                  "Кліщі, молоток, викрутки",
                  "Пасатижі та шестигранники",
                  "Свічкові торцеві головки"
                ]
              },
              "ULTRA-110": {
                image: "/static/instruments/ULTRA-110.png",
                specs: [
                  "110 предметів у комплекті",
                  "Для легкових авто та вантажівок",
                  "Торцеві головки TORX",
                  "Свічкові торцеві головки",
                  "Популярний на СТО"
                ]
              },
              "ULTRA-112": {
                image: "/static/instruments/ULTRA-112.png",
                specs: [
                  "112 предметів у комплекті",
                  "Ударні торцеві головки",
                  "Для роботи з гайковертами",
                  "Ідентичний ULTRA-110 за призначенням",
                  "Професійне використання"
                ]
              },
              "DJS-200BCULTRA": {
                "image": "/static/instruments/DJS-200BCULTRA.png",
                "specs": [
                  "Акумуляторний лобзик",
                  "Глибина різу дерева: 135 мм",
                  "800-2600 об/хв",
                  "Амплітуда коливання: 26 мм",
                  "Лита алюмінієва підошва"
                ]
              },
              "JS-100LX": {
                "image": "/static/instruments/JS-100LX.png",
                "specs": [
                  "Глибина різу дерева: 100 мм",
                  "800-3000 об/хв",
                  "Амплітуда коливання: 28 мм",
                  "Лита алюмінієва підошва",
                  "Підсвітка знімається з кнопки"
                ]
              },
              "JS-80LX": {
                "image": "/static/instruments/JS-80LX.png",
                "specs": [
                  "Глибина різу дерева: 80 мм",
                  "800-2900 об/хв",
                  "Амплітуда коливання: 22 мм",
                  "Лита алюмінієва підошва",
                  "Максимальний контроль різу"
                ]
              },
              "JS-65LX": {
                "image": "/static/instruments/JS-65LX.png",
                "specs": [
                  "Глибина різу дерева: 65 мм",
                  "800-2800 об/хв",
                  "Амплітуда коливання: 22 мм",
                  "Штампована сталева підошва",
                  "Для монтажних робіт"
                ]
              },
              "PS-30S": {
                "image": "/static/instruments/PS-30S.png",
                "specs": [
                  "Вібраційна шліфмашина",
                  "Потужність: 200 Вт",
                  "6000-13000 коливань/хв",
                  "Підошва: 90 х 182 мм",
                  "Амплітуда: 2 мм"
                ]
              },
              "PE-29S": {
                "image": "/static/instruments/PE-29S.png",
                "specs": [
                  "Ексцентрикова шліфмашина",
                  "Потужність: 290 Вт",
                  "7500-12000 об/хв",
                  "Підошва: 125 мм",
                  "Амплітуда: 2.5 мм"
                ]
              },
              "PE-50S": {
                "image": "/static/instruments/PE-50S.png",
                "specs": [
                  "Ексцентрикова шліфмашина",
                  "Потужність: 380 Вт",
                  "6000-13000 об/хв",
                  "Підошва: 125 мм",
                  "Амплітуда: 2 мм"
                ]
              },
              "PE-35RX": {
                "image": "/static/instruments/PE-35RX.png",
                "specs": [
                  "Ексцентрикова шліфмашина",
                  "Безщітковий двигун 350 Вт",
                  "4000-10000 об/хв",
                  "Підошва: 150 мм",
                  "Амплітуда: 5 мм"
                ]
              },
              "DSO-200BCULTRA": {
                "image": "/static/instruments/DSO-200BCULTRA.png",
                "specs": [
                  "Акумуляторна ексцентрикова",
                  "Напруга: 20 В",
                  "6000-12000 об/хв",
                  "Підошва: 125 мм",
                  "Амплітуда: 3 мм"
                ]
              },
              "BS-100S": {
                "image": "/static/instruments/BS-100S.png",
                "specs": [
                  "Стрічкова шліфмашина",
                  "Потужність: 1050 Вт",
                  "Швидкість стрічки: 200-380 м/хв",
                  "Розмір стрічки: 533 х 76 мм",
                  "Вага: 3.7 кг"
                ]
              },
              "DSC-200BCULTRA": {
                "image": "/static/instruments/DSC-200BCULTRA.png",
                "specs": [
                  "Акумуляторна циркулярна пила",
                  "Безщітковий двигун 20V",
                  "Глибина пропилу: 55 мм",
                  "Захист від заклинювання диска",
                  "Динамічне гальмо"
                ]
              },
              "DSC-201BC": {
                "image": "/static/instruments/DSC-201BC.png", 
                "specs": [
                  "Акумуляторна циркулярна пила",
                  "Потужність: 20V",
                  "Для виїзних робіт",
                  "Легка та мобільна",
                  "Патрубок для пилососа"
                ]
              },
              "CS-235IN": {
                "image": "/static/instruments/CS-235IN.png",
                "specs": [
                  "Професійна циркулярна пила", 
                  "Глибина пропилу: 85 мм",
                  "Можливість стаціонарного встановлення",
                  "Розклинювальний ніж",
                  "Литий алюмінієвий підошва"
                ]
              },
              "CS-210": {
                "image": "/static/instruments/CS-210.png",
                "specs": [
                  "Універсальна циркулярна пила",
                  "Глибина пропилу: 75 мм", 
                  "Для професійних користувачів",
                  "Для твердих заготовок",
                  "Литий алюмінієвий підошва"
                ]
              },
              "CS-185LX": {
                "image": "/static/instruments/CS-185LX.png",
                "specs": [
                  "Удосконалена циркулярна пила",
                  "Глибина пропилу: 62 мм",
                  "Для тривалих робіт",
                  "Литий алюмінієвий підошва", 
                  "Патрубок для пилососа"
                ]
              },
              "CS-185M": {
                "image": "/static/instruments/CS-185M.png",
                "specs": [
                  "Базова циркулярна пила",
                  "Глибина пропилу: 62 мм",
                  "Мала вага та компактність",
                  "Штампований алюмінієвий підошва",
                  "Для будівельних робіт"
                ]
              }
            };

models.forEach((model) => {
        const data = modelData[model];
        if (!data) return;

        const button = document.createElement("button");
        button.className = "model-button";

        // Фото моделі
        const img = document.createElement("img");
        img.src = data.image;
        img.alt = model;
        img.style.width = "100px";
        img.style.display = "block";
        img.style.margin = "0 auto 10px";
        button.appendChild(img);

        // Назва моделі
        const title = document.createElement("div");
        title.textContent = model;
        title.style.fontWeight = "bold";
        title.style.textAlign = "center";
        button.appendChild(title);

        // Кнопка "Детальніше"
        const detailBtn = document.createElement("button");
        detailBtn.className = "detail-view-btn";
        detailBtn.textContent = "Детальніше";
        detailBtn.onclick = (e) => {
            e.stopPropagation(); // Запобігаємо спливанню події до батьківської кнопки
            showModelDetail(model, data);
        };
        button.appendChild(detailBtn);

        // Обробник кліку на всю кнопку
        button.onclick = () => {
            addMessage(`Обираю модель: ${model}`, true);
            sendModelChoice(model);
        };

        userInput.disabled = true;
        sendButton.disabled = true;
        recordBtn.disabled = true;
        userInput.placeholder = "Оберіть модель зі списку..."; // Додатковий індикатор

        modelsButtons.appendChild(button);
    });

    modelOverlay.style.display = "flex";
    userInput.style.display = "none";
    sendButton.style.display = "none";
}

const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);

function showModelDetail(model, data) {
    const modal = document.getElementById("modelDetailModal");
      if (isIOS) {
        // Спеціальна логіка для iOS
        modal.style.animation = 'none';
        modal.offsetHeight; /* Trigger reflow */
        modal.style.animation = null; 
      }
    const image = document.getElementById("detailModelImage");
    const title = document.getElementById("detailModelTitle");
    const specsList = document.getElementById("detailModelSpecs");
    
    // Заповнюємо дані
    image.src = data.image;
    image.alt = model;
    title.textContent = model;
    
    // Очищаємо попередні специфікації
    specsList.innerHTML = "";
    
    // Додаємо всі характеристики
    data.specs.forEach(spec => {
        const li = document.createElement("li");
        li.textContent = spec;
        specsList.appendChild(li);
    });
    
    // Показуємо модальне вікно з анімацією
    modal.style.display = "flex";
    modal.classList.remove("closing");
    
    // Додамо анімацію для зображення
    image.style.opacity = "0";
    image.style.transform = "translateY(10px)";
    setTimeout(() => {
      image.style.transition = "opacity 0.3s ease-out, transform 0.3s ease-out";
      image.style.opacity = "1";
      image.style.transform = "translateY(0)";
    }, 100);
  }

  function closeModelDetail() {
    const modal = document.getElementById("modelDetailModal");
    modal.classList.add("closing");
    
    // Зачекаємо завершення анімації перед приховуванням
    setTimeout(() => {
      modal.style.display = "none";
    }, 300);
  }

  // Додамо плавний hover-ефект для кнопки "Детальніше"
  document.querySelectorAll('.detail-view-btn').forEach(btn => {
    btn.addEventListener('mouseenter', () => {
      btn.style.transform = "scale(1.05)";
    });
    btn.addEventListener('mouseleave', () => {
      btn.style.transform = "scale(1)";
    });
  });

function closeModelDetail() {
    document.getElementById("modelDetailModal").style.display = "none";
}

        function hideModelButtons() {
            modelOverlay.style.display = "none";
            userInput.style.display = "block";
            sendButton.style.display = "inline-block";
            modelsButtons.innerHTML = "";
        }

async function sendModelChoice(model) {
    hideModelButtons();
    document.getElementById("choose-model-btn").style.display = "none";
    showTypingIndicator();

    document.getElementById("progressHint").style.display = "none";
    document.getElementById("progressContainer").style.display = "none";

    userInput.disabled = false;
    sendButton.disabled = false;
    recordBtn.disabled = false; 
    userInput.placeholder = "Напишіть ваше повідомлення...";
    userInput.focus();

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: `Обираю модель: ${model}`, seller_name: sellerName }),
            credentials: "include"
        });

        const data = await response.json();

        // Оновлюємо stage, якщо сервер його повернув
        if (data.stage !== undefined) {
            updateStageIndicator(data.stage);
        }

        // ДОДАЄМО ОБРОБКУ ПІДКАЗКИ ПРО ВИБІР МОДЕЛІ
        if (data.model_feedback) {
            showModelFeedback(data.model_feedback);
        }

        // Додаємо повідомлення тільки якщо це не перехід на stage 3
        if (!data.stage || data.stage !== 3) {
            addMessage(data.reply, false);
            playVoice(data.reply);
        }

        // Обробка переходу на stage 3
        if (data.stage === 3) {
            if (data.model_chosen === false) {
                addMessage("На жаль, ця модель не підходить.", false);
            }
            addMessage(data.reply, false);
            playVoice(data.reply);
        }

        // Показ моделей або завершення чату
        if (data.show_models && data.models?.length) {
            showModelButtons(data.models, "Оберіть модель:", data.attempts_left || 1);
            modelsButtons.innerHTML = ""
        } else if (data.chat_ended) {
            disableChat();
            if (data.show_restart_button) {
                restartButton.style.display = "inline-block";
            }
        }

    } catch (error) {
        console.error("Помилка:", error);
        addMessage("Помилка зв'язку. Спробуйте ще раз.", false);
    } finally {
        hideTypingIndicator();
    }
}

// ФУНКЦІЯ ДЛЯ ВІДОБРАЖЕННЯ ПІДКАЗКИ ПРО ВИБІР МОДЕЛІ
function showModelFeedback(feedbackText) {
    // Визначаємо тип підказки на основі тексту
    let toastType = 'info';
    if (feedbackText.includes('✅')) {
        toastType = 'success';
    } else if (feedbackText.includes('❌')) {
        toastType = 'error';
    } else if (feedbackText.includes('⚠️')) {
        toastType = 'warning';
    }
    
    // Використовуємо вже існуючу функцію showFeedback або створюємо нову
    if (typeof showFeedback === 'function') {
        showFeedback(feedbackText, toastType);
    } else {
        // Альтернативна реалізація, якщо функції showFeedback немає
        createFeedbackToast(feedbackText, toastType);
    }
}

// АЛЬТЕРНАТИВНА ФУНКЦІЯ, ЯКЩО showFeedback НЕ ІСНУЄ
function createFeedbackToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `feedback-toast ${type}`;
    
    toast.innerHTML = `
        <div class="feedback-toast-content">
            <span class="feedback-toast-close">&times;</span>
            <div class="feedback-toast-message">${message}</div>
        </div>
    `;
    
    document.body.appendChild(toast);
    
    // Додаємо обробник закриття
    const closeBtn = toast.querySelector('.feedback-toast-close');
    closeBtn.addEventListener('click', () => {
        toast.style.animation = 'slideUp 0.5s ease-out forwards';
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 500);
    });
    
    // Автоматичне закриття через 5 секунд
    setTimeout(() => {
        if (toast.parentNode) {
            toast.style.animation = 'slideUp 0.5s ease-out forwards';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 500);
        }
    }, 5000);
}

function createModelButton(model) {
    const button = document.createElement("button");
    button.innerText = model;
    button.onclick = () => {
        addMessage(`Обираю модель: ${model}`, true);
        sendModelChoice(model);
    };
    return button;
}

function updateStageIndicator(stage) {
    document.querySelectorAll(".stage-item").forEach(item => {
        const dot = item.querySelector(".stage-dot");
        const itemStage = parseInt(item.dataset.stage);

        dot.classList.remove("active", "completed");

        if (itemStage < stage) {
            dot.classList.add("completed");
        } else if (itemStage === stage) {
            dot.classList.add("active");
        }
    });
}


function updateStageProgress(currentStage) {
  const progressPercent = ((currentStage - 1) / 3) * 100; // 4 етапи, але прогресс бар на 3 кроки
  questionProgressBar.style.width = `${progressPercent}%`;
  
  // Оновлюємо точки етапів
  for (let i = 1; i <= 4; i++) {
    const dot = document.getElementById(`stage-dot-${i}`);
    if (!dot) continue;
    
    if (i < currentStage) {
      dot.classList.add('completed');
      dot.classList.remove('active');
    } else if (i === currentStage) {
      dot.classList.add('active');
      dot.classList.remove('completed');
    } else {
      dot.classList.remove('active', 'completed');
    }
  }
}

let sellerName = '';
let selectedCategory = '';

async function authenticateSeller(name, category) {
  try {
    const response = await fetch("/authenticate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        seller_name: name,
        category: category
      }),
      credentials: "include"
    });
    return await response.json();
  } catch (error) {
    console.error("Помилка автентифікації:", error);
    return { error: "Помилка з'єднання" };
  }
}

function initializeCategorySelection() {
  const categoryButtonsContainer = document.getElementById('category-selection-buttons');
  
  const availableCategories = [
    { value: "screwdrivers", name: "Шуруповерти" },
    { value: "grinders", name: "КШМ (болгарки)" },
    { value: "hammers", name: "Перфоратори" },
    { value: "inverters", name: "Інвертори" },
    { value: "saws", name: "Ланцюгові пили" },
    { value: "trimmers", name: "Тримери" },
    { value: "sprayers", name: "Обприскувачі" },
    { value: "busters", name: "Пускові та зарядні" },
    { value: "compresor", name: "Компресори" },
    { value: "impact", name: "Гвинтоверти та гайковерти" },
    { value: "showers", name: "Мийки високого тиску" },
    { value: "lighters", name: "Акумуляторні ліхтарі" },
    { value: "instuments", name: "Набори Ultra" },
    { value: "jigsaw", name: "Лобзики" },
    { value: "woodgrinders", name: "Шліфмашини" },
    { value: "circularsaws", name: "Циркулярні пили" }
  ];
  
  availableCategories.forEach(category => {
    const button = document.createElement('button');
    button.textContent = category.name;
    button.dataset.value = category.value;

    button.addEventListener('click', () => {
      document.querySelectorAll('#category-selection-buttons button').forEach(btn => {
        btn.classList.remove('selected-category');
      });
      button.classList.add('selected-category');
      selectedCategory = category.value;
      document.getElementById('confirm-category-btn').style.display = 'block';
    });

    categoryButtonsContainer.appendChild(button);
  });

  document.getElementById('confirm-category-btn').addEventListener('click', () => {
    if (selectedCategory) {
      const categoryName = availableCategories.find(cat => cat.value === selectedCategory)?.name || selectedCategory;
      document.getElementById('selected-category-name').textContent = categoryName;
      document.getElementById('category-selection-modal').style.display = 'none';
      document.getElementById('auth-modal').style.display = 'flex';
      document.getElementById('seller-name-input').focus();
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  const modeModal = document.getElementById('mode-selection-modal');
  const categoryModal = document.getElementById('category-selection-modal');
  const authModal = document.getElementById('auth-modal');
  const rulesModal = document.getElementById('rules-modal');
  const nameInput = document.getElementById('seller-name-input');
  const submitButton = document.getElementById('submit-name-btn');

  rulesModal.style.display = 'none';
  categoryModal.style.display = 'none';
  authModal.style.display = 'none';

  initializeCategorySelection();

  document.getElementById('training-mode-btn').addEventListener('click', () => {
    modeModal.style.display = 'none';
    categoryModal.style.display = 'flex';
  });

  document.getElementById('exam-mode-btn').addEventListener('click', () => {
    selectedCategory = "exam";
    document.getElementById('selected-category-info').style.display = 'none';
    modeModal.style.display = 'none';
    authModal.style.display = 'flex';
    nameInput.focus();
  });

  submitButton.addEventListener('click', async () => {
    const name = nameInput.value.trim();

    if (!name) {
      alert("Будь ласка, введіть ваше ПІБ.");
      nameInput.focus();
      return;
    }

    nameInput.disabled = true;
    submitButton.disabled = true;

    const result = await authenticateSeller(name, selectedCategory);

    if (result.error) {
      alert("Помилка: " + result.error);
      nameInput.disabled = false;
      submitButton.disabled = false;
    } else {
      sellerName = name;
      authModal.style.display = 'none';
      rulesModal.style.display = 'flex';
    }
  });

  // ✅ Ось тут ми додаємо кнопку "Назад"
  document.getElementById('back-to-category-select').addEventListener('click', () => {
    // Якщо ЕКЗАМЕН → назад до вибору режиму
    if (selectedCategory === "exam") {
      selectedCategory = '';
      authModal.style.display = 'none';
      document.getElementById('selected-category-info').style.display = 'block';
      modeModal.style.display = 'flex';
    } 
    // Якщо ТРЕНУВАННЯ → назад до вибору категорій
    else {
      authModal.style.display = 'none';
      categoryModal.style.display = 'flex';
    }
  });
});

function playVoice(text) {
    // Перевіряємо, чи це exam режим
    if (selectedCategory !== "exam") {
        return; // Не програємо озвучку для інших категорій
    }
    
    fetch("/speak", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text })
    })
    .then(res => {
        if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status}`);
        }
        return res.blob();
    })
    .then(blob => {
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        audio.play();
    })
    .catch(err => {
        console.error("TTS error:", err);
        // Можна додати повідомлення про помилку, але не обов'язково
    });
}

let isCooldown = false;
let chatEnded = false;

async function sendMessage() {
    const message = userInput.value.trim();
    if (!sellerName) {
        alert("Будь ласка, спочатку введіть ваші дані");
        return;
    }

    if (!message) return;

    addMessage(message, true);
    userInput.value = '';
    showTypingIndicator();
    statusElement.textContent = "Клієнт набирає відповідь...";

    isCooldown = true;
    userInput.disabled = true;
    sendButton.disabled = true;

    setTimeout(() => {
        if (!chatEnded) {
            isCooldown = false;
            userInput.disabled = false;
            sendButton.disabled = false;
            statusElement.textContent = "";
        }
    }, 4000);

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ message, seller_name: sellerName }),
            credentials: "include"
        });

        if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
        const data = await response.json();

        // --- ОБРОБКА FEEDBACK ДЛЯ ВСІХ ЕТАПІВ ---
        if (data.question_feedback) {
            showFeedbackToast(data.question_feedback, data.question_score || 0);
        }
        
        // 🔴 ОБРОБКА ПІДКАЗОК ДЛЯ STAGE 3
        if (data.answer_feedback) {
            showFeedbackToast(data.answer_feedback, data.current_score || 0);
        }
        
        // 🔴 ОБРОБКА ПІДКАЗОК ДЛЯ ВИБОРУ МОДЕЛІ
        if (data.model_feedback) {
            showFeedbackToast(data.model_feedback);
        }
        
        // 🔴 ОБРОБКА ПІДКАЗОК ДЛЯ STAGE 4 (ЗАПЕРЕЧЕННЯ)
        if (data.objection_feedback) {
            showFeedbackToast(data.objection_feedback, 'objection-info');
        }

        // Обробка відповіді
        if (data.error) {
            statusElement.textContent = "Помилка: " + data.error;
            if (data.chat_ended) {
                chatEnded = true;
                disableChat();
            }
            return;
        }

        // --- Обробка фінальної оцінки ---
if (data.detailed_report) {
    addMessage(data.reply, false);
    playVoice(data.reply);
    
    // 🔴 ПОКАЗУЄМО МОДАЛЬНЕ ВІКНО З ДЕТАЛЬНИМ ЗВІТОМ
    setTimeout(() => {
        showDetailedReport(data.detailed_report);
    }, 1000);
} else if (data.evaluation) {
    // Стара логіка для зворотної сумісності
    addMessage(data.reply, false);
    playVoice(data.reply);
    
    setTimeout(() => {
        addMessage(data.evaluation, false);
        playVoice(data.evaluation);
    }, 1000);
}
        // --- Логіка для етапу 3 (технічні питання) ---
        else if (data.stage === 3) {
            addMessage(data.reply, false);
            statusElement.textContent = "Клієнт уточнює деталі про модель...";
            userInput.focus();
            playVoice(data.reply);

            // 🔴 ВІДОБРАЖЕННЯ ПІДСУМКУ БАЛІВ ПІСЛЯ ОСТАННЬОЇ ВІДПОВІДІ
            if (data.answers_summary) {
                setTimeout(() => {
                    showFeedbackToast(data.answers_summary, 'info');
                }, 500);
            }

            if (data.questions) {
                data.questions.forEach((question, index) => {
                    setTimeout(() => {
                        addMessage(question, false);
                        chatContainer.scrollTop = chatContainer.scrollHeight;
                    }, (index + 1) * 1000);
                });
            }
        }
        // 🔴 ЛОГІКА ДЛЯ ЕТАПУ 4 (ЗАПЕРЕЧЕННЯ)
        else if (data.stage === 4) {
            addMessage(data.reply, false);
            
            // Оновлюємо статус відповідно до раунду
            if (data.current_round === 1) {
                statusElement.textContent = "Клієнт обмірковує вашу відповідь...";
            } else if (data.current_round === 2) {
                statusElement.textContent = "Клієнт приймає остаточне рішення...";
            }
            
            userInput.focus();
            playVoice(data.reply);
        }
        else {
            // Для інших етапів - стандартна обробка
            if (data.reply) {
                addMessage(data.reply, false);
                playVoice(data.reply);
            }
        }

        // --- СТАНДАРТНА ОБРОБКА ДАНИХ ---
        if (data.show_restart_button) {
            restartButton.style.display = "inline-block";
        } else {
            restartButton.style.display = "none";
        }

        if (data.hide_choose_model_btn) {
            document.getElementById("choose-model-btn").style.display = "none";
        }

        if (data.show_models) {
            showModelButtons(data.models, "Оберіть модель:", data.attempts_left);
        }

        if (data.show_model_button) {
            document.getElementById("choose-model-btn").classList.remove("hidden");
        }

        if (data.stage !== undefined) {
            updateStageIndicator(data.stage);
            
            // 🔴 ОНОВЛЮЄМО СТАТУС ВІДПОВІДНО ДО ЕТАПУ
            switch(data.stage) {
                case 1:
                    statusElement.textContent = "Клієнт очікує на ваші питання...";
                    break;
                case 2:
                    statusElement.textContent = "Оберіть модель інструменту";
                    break;
                case 3:
                    statusElement.textContent = "Клієнт уточнює деталі про модель...";
                    break;
                case 4:
                    statusElement.textContent = "Клієнт висловив заперечення...";
                    break;
            }
        }

        if (data.question_progress !== undefined) {
            updateProgressBar(data.question_progress, 5);
        }

        if (data.chat_ended) {
            chatEnded = true;
            disableChat();

            if (data.show_restart_button) {
                restartButton.style.display = "inline-block";
            }

            if (data.model_chosen) {
                setTimeout(() => {
                    addMessage("Дякую! Я беру цю модель.", false);
                }, 1000);
            }

            // 🔴 ВІДОБРАЖЕННЯ ФІНАЛЬНИХ БАЛІВ
            if (data.objection_score !== undefined && data.total_score !== undefined) {
                setTimeout(() => {
                    showFeedbackToast(`🎯 За заперечення: ${data.objection_score}/8 балів | Загальний результат: ${data.total_score}/30`, 'success');
                }, 2000);
            }

            return;
        } else {
            // Якщо чат не завершено, але немає спеціального статусу - очищаємо
            if (!data.stage) {
                statusElement.textContent = "";
            }
        }

    } catch (error) {
        console.error("Помилка:", error);
        statusElement.textContent = "Помилка з'єднання";
        addMessage("Вибачте, сталася помилка. Спробуйте ще раз.", false);
    } finally {
        hideTypingIndicator();
    }
}

// Функція для показу плаваючого сповіщення
// Функція для показу плаваючого сповіщення
function showFeedbackToast(message, score = 0) {
    const toast = document.getElementById('feedback-toast');
    const messageElement = document.getElementById('feedback-toast-message');
    
    // Визначаємо тип сповіщення
    let type = 'info';
    
    // Для stage 1 та stage 2 (питання та модель)
    if (typeof score === 'number') {
        if (score === 0 || message.includes('❌') || message.includes('не стосується') || message.includes('неправильне')) {
            type = 'error';
        } else if (score === 1 || message.includes('⚠️') || message.includes('краще') || message.includes('потрібно краще')) {
            type = 'warning';
        } else if (score === 2 || message.includes('✅') || message.includes('відмінно') || message.includes('чудово')) {
            type = 'success';
        }
    } 
    // Для stage 3 (відповіді на технічні питання)
    else if (typeof score === 'string') {
        if (score.startsWith('answer-')) {
            type = score;
        }
        // 🔴 ДЛЯ STAGE 4 (ЗАПЕРЕЧЕННЯ)
        else if (score === 'objection-info') {
            type = 'objection-info';
        }
    }
    // Для текстових підказок
    else if (message.includes('❌') && (message.includes('не по темі') || message.includes('неправильну модель') || message.includes('Потрібно більш переконливі'))) {
        type = 'error';
    } else if (message.includes('⚠️') && (message.includes('характеристику') || message.includes('Добре, але'))) {
        type = 'warning';
    } else if (message.includes('✅') && (message.includes('Відмінна відповідь') || message.includes('Відмінно'))) {
        type = 'success';
    } else if (message.includes('Загальний бал за відповіді') || message.includes('За заперечення:')) {
        type = 'info';
    } else if (message.includes('💡') && message.includes('заперечення')) {
        type = 'objection-info';
    }
    
    // Очищаємо попередні класи
    toast.className = 'feedback-toast';
    toast.classList.add(type);
    
    // Встановлюємо повідомлення
    messageElement.textContent = message;
    
    // Показуємо сповіщення
    toast.classList.remove('hidden');
    
    // Автоматичне закриття через різний час в залежності від типу
    let timeout = 5000;
    if (type.includes('error') || type.includes('warning')) {
        timeout = 8000; // Більше часу для помилок
    } else if (type.includes('info') && (message.includes('Загальний бал') || message.includes('За заперечення'))) {
        timeout = 10000; // Ще більше часу для підсумку
    } else if (type.includes('objection-info')) {
        timeout = 6000; // Для підказок stage 4
    }
    
    setTimeout(() => {
        hideFeedbackToast();
    }, timeout);
}

// Функція для приховування сповіщення
function hideFeedbackToast() {
    const toast = document.getElementById('feedback-toast');
    toast.style.animation = 'slideUp 0.5s ease-out forwards';
    
    setTimeout(() => {
        toast.classList.add('hidden');
        toast.style.animation = '';
    }, 500);
}

// Додаємо обробник для кнопки закриття
document.addEventListener('DOMContentLoaded', function() {
    const closeBtn = document.querySelector('.feedback-toast-close');
    if (closeBtn) {
        closeBtn.addEventListener('click', hideFeedbackToast);
    }
});

let mediaRecorder;
let audioChunks = [];

const recordBtn = document.getElementById("record-btn");
const recordingIndicator = document.getElementById("recording-indicator");

recordBtn.addEventListener("click", async () => {
  if (!mediaRecorder || mediaRecorder.state === "inactive") {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // ✅ Визначаємо підтримуваний формат
      let mimeType = "audio/webm";
      if (MediaRecorder.isTypeSupported("audio/mp4")) {
        mimeType = "audio/mp4";
      } else if (MediaRecorder.isTypeSupported("audio/m4a")) {
        mimeType = "audio/m4a";
      }

      // ✅ Передаємо mimeType у MediaRecorder
      mediaRecorder = new MediaRecorder(stream, { mimeType });

      mediaRecorder.ondataavailable = event => {
        audioChunks.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        recordingIndicator.style.display = "none";
        mediaRecorder.stream.getTracks().forEach(track => track.stop());

        // ✅ Використовуємо правильний MIME і розширення
        const audioBlob = new Blob(audioChunks, { type: mimeType });
        audioChunks = [];

        const ext = mimeType.includes("mp4") ? "mp4" : "webm";
        const formData = new FormData();
        formData.append("file", audioBlob, `voice.${ext}`);

        try {
          const response = await fetch("/speech-to-text", {
            method: "POST",
            body: formData
          });

          if (!response.ok) {
            addMessage("❌ Помилка сервера розпізнавання", false);
            return;
          }

          const data = await response.json();
          if (data.error) {
            addMessage("❌ " + data.error, false);
          } else if (data.text) {
            userInput.value = data.text;
            sendMessage();
          } else {
            addMessage("❌ Відповідь без тексту", false);
          }
        } catch (err) {
          console.error("STT fetch error:", err);
          addMessage("❌ Помилка відправки голосу", false);
        }
      };

      mediaRecorder.start();
      recordBtn.textContent = "⏹ Зупинити";
      recordingIndicator.style.display = "block";
    } catch (err) {
      console.error("Mic error:", err);
      addMessage("❌ Немає доступу до мікрофона", false);
    }
  } else {
    mediaRecorder.stop();
    recordBtn.textContent = "🎤";
  }
});

// Додайте ці функції
function showDetailedReport(reportData) {
    const modal = document.getElementById('report-modal');
    const content = document.getElementById('report-content');
    
    // Визначаємо клас для фінальної оцінки
    let finalClass = 'poor';
    if (reportData.total_score >= 24) finalClass = 'excellent';
    else if (reportData.total_score >= 16) finalClass = 'good';
    
    // Формуємо HTML звіту з ТРЬОМА окремими блоками
    content.innerHTML = `
        <div class="report-final ${finalClass}">
            ${reportData.summary_label}
        </div>
        
        <div class="report-section">
            <h3>📈 Детальні бали:</h3>
            <div class="report-details">
                <div class="report-score">За модель: ${reportData.model_score}/4 балів</div>
                <div class="report-score">За питання: ${reportData.questions_score}/8 балів</div>
                <div class="report-score">За відповіді: ${reportData.answers_score}/10 балів</div>
                <div class="report-score">За заперечення: ${reportData.objection_score}/8 балів</div>
                <div class="report-score" style="font-size: 20px; margin-top: 10px;">
                    Загальний результат: ${reportData.total_score}/30 балів
                </div>
            </div>
        </div>
        
        <!-- 🔴 БЛОК ДЛЯ STAGE 1 - ВИЯВЛЕННЯ ПОТРЕБ -->
        <div class="report-section">
            <h3>🔍 Аналіз виявлення потреб:</h3>
            <div class="report-details">
                <strong>Оцінка якості виявлення потреб:</strong><br>
                ${reportData.stage1_analysis || "Аналіз недоступний"}
            </div>
            <div class="report-advice">
                <strong>💡 Поради для покращення виявлення потреб:</strong><br>
                ${reportData.stage1_advice || "Рекомендації відсутні"}
            </div>
        </div>
        
        <!-- 🔴 БЛОК ДЛЯ STAGE 3 - ПРЕЗЕНТАЦІЯ МОДЕЛІ -->
        <div class="report-section">
            <h3>🎯 Аналіз презентації моделі:</h3>
            <div class="report-details">
                <strong>Оцінка якості презентації:</strong><br>
                ${reportData.stage3_analysis || "Аналіз недоступний"}
            </div>
            <div class="report-advice">
                <strong>💡 Поради для покращення презентації:</strong><br>
                ${reportData.stage3_advice || "Рекомендації відсутні"}
            </div>
        </div>
        
        <!-- 🔴 БЛОК ДЛЯ STAGE 4 - РОБОТА З ЗАПЕРЕЧЕННЯМИ -->
        <div class="report-section">
            <h3>🛡️ Аналіз роботи з запереченнями:</h3>
            <div class="report-details">
                <strong>Оцінка роботи з запереченнями:</strong><br>
                ${reportData.stage4_analysis || "Аналіз недоступний"}
            </div>
            <div class="report-advice">
                <strong>💡 Поради для роботи з запереченнями:</strong><br>
                ${reportData.stage4_advice || "Рекомендації відсутні"}
            </div>
        </div>
        
        <div style="text-align: center; margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
            <strong>📋 Звіт збережено для вашого тренера</strong>
        </div>
    `;
    
    modal.style.display = 'flex';
}

function hideDetailedReport() {
    const modal = document.getElementById('report-modal');
    modal.style.display = 'none';
}

// Обробник для кнопки "Ознайомлений"
document.getElementById('accept-report-btn').addEventListener('click', function() {
    hideDetailedReport();
    // Додаємо фінальне повідомлення в чат
    addMessage("Результат консультації: " + document.querySelector('.report-final').textContent + ". Звіт збережено для вашого тренера.", false);
});

// Додайте обробник для закриття модального вікна по кліку на backdrop
document.getElementById('report-modal').addEventListener('click', function(e) {
    if (e.target === this) {
        hideDetailedReport();
        // Все одно додаємо повідомлення в чат
        const finalElement = document.querySelector('.report-final');
        if (finalElement) {
            addMessage("Результат консультації: " + finalElement.textContent + ". Звіт збережено для вашого тренера.", false);
        }
    }
});

    // Стартове повідомлення при завантаженні
    document.getElementById('accept-rules-btn').addEventListener('click', async () => {
      const rulesModal = document.getElementById('rules-modal');
      rulesModal.style.display = 'none';

      // Починаємо чат
      try {
        const response = await fetch("/start_chat");
        const data = await response.json();

        if (data.reply) {
          addMessage(data.reply, false);
          playVoice(data.reply);     // додаємо перше повідомлення
          unblockChat();                       // розблоковуємо поле вводу
          userInput.focus();
          showStageIndicator();                // показуємо індикатор етапів

          // Зміна зображення клієнта
      const clientCharacter = document.getElementById("client-character");
      const clientAvatar = document.getElementById("client-avatar");

      if (data.avatar) {
        clientAvatar.src = `/static/avatars/${data.avatar}`;
      }
      clientCharacter.style.display = "block";
      {
          }
        }
      } catch (err) {
        console.error("Помилка при старті чату:", err);
        addMessage("Помилка при старті чату. Спробуйте ще раз.", false);
      }
    });

    document.querySelector(".model-detail-close").addEventListener("click", closeModelDetail);

    document.getElementById("modelDetailModal").addEventListener("click", function(e) {
        if (e.target === this) {
            closeModelDetail();
        }
    });

      document.addEventListener('DOMContentLoaded', function() {
        const closeHintBtn = document.getElementById("close-hint-btn");
        if (closeHintBtn) {
            closeHintBtn.addEventListener("click", hideModelHint);
        } else {
            console.error("Кнопка закриття підказки не знайдена");
        }
    });

document.getElementById("choose-model-btn").addEventListener("click", async () => {
    try {
        const response = await fetch("/show_models", { method: "POST" });
        const data = await response.json();

        if (data.models && data.models.length) {
            showModelButtons(data.models);
            document.getElementById("choose-model-btn").classList.add("hidden");
        }
    } catch (err) {
        addMessage("Помилка при завантаженні моделей. Спробуйте ще раз.", false);
    }
});

    document.getElementById("close-model-overlay").addEventListener("click", () => {
        hideModelButtons(); // ❌ не викликаємо sendModelChoice()
        document.getElementById("choose-model-btn").classList.remove("hidden"); // повертаємо кнопку
    });
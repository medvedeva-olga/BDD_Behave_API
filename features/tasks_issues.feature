# language: en

@tasks @issues
Feature: Задачи Tasks API

  Background:
    Given мок находится в начальном состоянии

  @smoke
  Scenario: Задача из начальных данных доступна по ID
    When я запрашиваю задачу с ID 1
    Then статус ответа равен 200
    And ответ соответствует схеме "issue_response"
    And поле "issue.subject" равно "Project management"
    And поле "issue.parentIssue" равно null
    And даты задачи равны "2026-01-01" и "2026-12-31"

  @smoke
  Scenario: Создание задачи возвращает ID и сохраняет поля
    When я создаю задачу
      | поле      | значение          |
      | subject   | Проверка создания |
      | projectId | 854               |
      | trackerId | 34                |
      | statusId  | 13                |
      | priority  | 185               |
      | startDate | 2026-05-01        |
      | endDate   | 2026-05-10        |
    Then статус ответа равен 201
    And тело ответа содержит ID новой задачи
    When я запрашиваю созданную задачу
    Then статус ответа равен 200
    And ответ соответствует схеме "issue_response"
    And поле "issue.id" равно ID созданной задачи
    And поле "issue.subject" равно "Проверка создания"
    And поле "issue.parentIssue" равно null
    And даты задачи равны "2026-05-01" и "2026-05-10"

  Scenario: Дочерняя задача привязывается к существующему родителю
    When я создаю задачу с родителем 1
      | поле      | значение        |
      | subject   | Дочерняя задача |
      | startDate | 2026-06-01      |
      | endDate   | 2026-06-30      |
    Then статус ответа равен 201
    And тело ответа содержит ID новой задачи
    When я запрашиваю дочерние задачи для ID 1
    Then список детей содержит созданную задачу
    When я запрашиваю созданную задачу
    Then поле "issue.parentIssue" равно числу 1

  @negative
  Scenario: Создание задачи с несуществующим родителем отклоняется
    When я создаю задачу с родителем 999
    Then статус ответа равен 404
    And ответ соответствует схеме "error"
    And сообщение об ошибке содержит "Parent issue 999 not found"

  @negative
  Scenario Outline: Создание задачи без обязательного поля отклоняется
    When я создаю задачу без поля "<поле>"
    Then статус ответа равен 400
    And ответ соответствует схеме "error"
    And сообщение об ошибке содержит "<поле>"
    Examples:
      | поле      |
      | projectId |
      | trackerId |
      | statusId  |
      | priority  |
      | subject   |

  @negative
  Scenario: Создание задачи с пустым subject отклоняется
    When я создаю задачу с пустым subject
    Then статус ответа равен 400
    And ответ соответствует схеме "error"
    And сообщение об ошибке содержит "subject"

  Scenario: Задача без дат возвращает null в standards
    When я создаю задачу без дат
    Then статус ответа равен 201
    And тело ответа содержит ID новой задачи
    When я запрашиваю созданную задачу
    Then поле "issue.standards.0.valueId" равно null
    And поле "issue.standards.1.valueId" равно null

BEGIN TRANSACTION;
CREATE TABLE "asistencia" (
  "id_asistencia" INTEGER PRIMARY KEY AUTOINCREMENT,
  "id_persona" INTEGER NOT NULL,
  "fecha" TEXT NOT NULL,
  "hora_entrada" TEXT,
  "hora_salida" TEXT,
  "estado" TEXT NOT NULL,
  "observaciones" TEXT NOT NULL,
  "id_usuario_registro" INTEGER,
  "created_at" TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY ("id_persona") REFERENCES "persona" ("id_persona") ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY ("id_usuario_registro") REFERENCES "usuario" ("id_usuario") ON DELETE CASCADE ON UPDATE CASCADE
);
INSERT INTO "asistencia" VALUES(1,11,'2026-11-14','07:53:00','12:13:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(2,12,'2026-11-14','07:53:00','12:08:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(3,13,'2026-11-14','07:48:00','12:18:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(4,14,'2026-11-14','07:36:00','12:12:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(5,15,'2026-11-14','07:47:00','12:11:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(6,16,'2026-11-14','08:37:00','12:19:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(7,17,'2026-11-14','07:54:00','12:30:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(8,18,'2026-11-14','08:40:00','12:13:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(9,19,'2026-11-14','08:33:00','12:07:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(10,20,'2026-11-14','08:57:00','12:16:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(11,21,'2026-11-14','07:53:00','12:19:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(12,22,'2026-11-14','08:32:00','12:22:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(13,23,'2026-11-14','08:48:00','12:11:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(14,24,'2026-11-14','07:51:00','12:12:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(15,25,'2026-11-14','07:57:00','12:12:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(16,26,'2026-11-14','08:27:00','12:13:00','Retraso','Retraso justificado en llegada',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(17,27,'2026-11-14','08:35:00','12:16:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(18,28,'2026-11-14','08:52:00','12:26:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(19,29,'2026-11-14','07:47:00','12:28:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(20,30,'2026-11-14','08:42:00','12:13:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(21,31,'2026-11-14',NULL,NULL,'Ausente','Inasistencia al taller sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(22,32,'2026-11-14','07:51:00','12:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(23,33,'2026-11-14','08:39:00','12:06:00','Retraso','Retraso justificado en llegada',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(24,34,'2026-11-14','07:55:00','12:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(25,35,'2026-11-14','07:36:00','12:23:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(26,36,'2026-11-14','08:25:00','12:11:00','Retraso','Retraso justificado en llegada',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(27,37,'2026-11-14','08:58:00','12:25:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(28,38,'2026-11-14','08:34:00','12:12:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(29,39,'2026-11-14','08:53:00','12:23:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(30,40,'2026-11-14','08:41:00','12:12:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(31,41,'2026-11-14',NULL,NULL,'Ausente','Inasistencia al taller sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(32,42,'2026-11-14','08:32:00','12:29:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(33,43,'2026-11-14','07:34:00','12:25:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(34,44,'2026-11-14','08:49:00','12:07:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(35,45,'2026-11-14','08:46:00','12:13:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(36,46,'2026-11-14',NULL,NULL,'Ausente','Inasistencia al taller sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(37,47,'2026-11-14','08:15:00','12:08:00','Retraso','Retraso justificado en llegada',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(38,48,'2026-11-14','08:54:00','12:25:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(39,49,'2026-11-14','08:43:00','12:10:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(40,50,'2026-11-14','08:46:00','12:29:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(41,51,'2026-11-14','07:57:00','12:25:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(42,52,'2026-11-14','07:34:00','12:16:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(43,53,'2026-11-14','07:49:00','12:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(44,54,'2026-11-14','07:41:00','12:30:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(45,55,'2026-11-14','07:37:00','12:23:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(46,56,'2026-11-14',NULL,NULL,'Ausente','Inasistencia al taller sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(47,57,'2026-11-14','08:56:00','12:07:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(48,11,'2026-11-20',NULL,NULL,'Ausente','Inasistencia al taller sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(49,12,'2026-11-20','07:34:00','12:26:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(50,13,'2026-11-20','07:38:00','12:21:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(51,14,'2026-11-20','08:28:00','12:11:00','Retraso','Retraso justificado en llegada',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(52,15,'2026-11-20',NULL,NULL,'Ausente','Inasistencia al taller sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(53,16,'2026-11-20','07:52:00','12:14:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(54,17,'2026-11-20','08:44:00','12:21:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(55,18,'2026-11-20','07:37:00','12:07:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(56,19,'2026-11-20','07:48:00','12:12:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(57,20,'2026-11-20','07:37:00','12:07:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(58,21,'2026-11-20','08:42:00','12:15:00','Retraso','Retraso justificado en llegada',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(59,22,'2026-11-20','07:38:00','12:26:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(60,23,'2026-11-20','07:53:00','12:23:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(61,24,'2026-11-20','07:55:00','12:20:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(62,25,'2026-11-20','07:33:00','12:08:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(63,26,'2026-11-20','08:43:00','12:18:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(64,27,'2026-11-20','07:51:00','12:25:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(65,28,'2026-11-20',NULL,NULL,'Ausente','Inasistencia al taller sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(66,29,'2026-11-20','08:53:00','12:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(67,30,'2026-11-20','07:37:00','12:11:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(68,31,'2026-11-20','08:34:00','12:18:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(69,32,'2026-11-20','08:37:00','12:07:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(70,33,'2026-11-20','07:31:00','12:25:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(71,34,'2026-11-20',NULL,NULL,'Ausente','Inasistencia al taller sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(72,35,'2026-11-20','07:54:00','12:12:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(73,36,'2026-11-20','08:45:00','12:11:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(74,37,'2026-11-20','08:43:00','12:06:00','Retraso','Retraso justificado en llegada',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(75,38,'2026-11-20','07:42:00','12:13:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(76,39,'2026-11-20',NULL,NULL,'Ausente','Inasistencia al taller sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(77,40,'2026-11-20','08:43:00','12:27:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(78,41,'2026-11-20',NULL,NULL,'Ausente','Inasistencia al taller sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(79,42,'2026-11-20',NULL,NULL,'Ausente','Inasistencia al taller sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(80,43,'2026-11-20','08:34:00','12:11:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(81,44,'2026-11-20','07:48:00','12:28:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(82,45,'2026-11-20','08:31:00','12:06:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(83,46,'2026-11-20','07:31:00','12:21:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(84,47,'2026-11-20','07:32:00','12:24:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(85,48,'2026-11-20','07:42:00','12:08:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(86,49,'2026-11-20',NULL,NULL,'Ausente','Inasistencia al taller sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(87,50,'2026-11-20','07:49:00','12:07:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(88,51,'2026-11-20','08:38:00','12:11:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(89,52,'2026-11-20','08:37:00','12:13:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(90,53,'2026-11-20','08:44:00','12:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(91,54,'2026-11-20',NULL,NULL,'Ausente','Inasistencia al taller sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(92,55,'2026-11-20',NULL,NULL,'Ausente','Inasistencia al taller sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(93,56,'2026-11-20','07:32:00','12:22:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(94,57,'2026-11-20','08:34:00','12:16:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(95,1,'2026-11-20','07:30:00','13:00:00','Presente','Jornada sabatina cumplida',1,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(96,2,'2026-11-20','07:30:00','13:00:00','Presente','Jornada sabatina cumplida',1,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(97,3,'2026-11-20','07:30:00','13:00:00','Presente','Jornada sabatina cumplida',1,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(98,4,'2026-11-20','07:30:00','13:00:00','Presente','Jornada sabatina cumplida',1,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(99,5,'2026-11-20','07:30:00','13:00:00','Presente','Jornada sabatina cumplida',1,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(100,6,'2026-11-20','07:30:00','13:00:00','Presente','Jornada sabatina cumplida',1,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(101,7,'2026-11-20','07:30:00','13:00:00','Presente','Jornada sabatina cumplida',1,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(102,8,'2026-11-20','07:30:00','13:00:00','Presente','Jornada sabatina cumplida',1,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(103,9,'2026-11-20','07:30:00','13:00:00','Presente','Jornada sabatina cumplida',1,'2026-11-20T14:36:52');
INSERT INTO "asistencia" VALUES(105,32,'2026-11-22','18:47:11',NULL,'Retraso','Llegada tardía autónoma (Turno Tarde > 12:45)',1,'2026-11-22 22:47:11');
INSERT INTO "asistencia" VALUES(106,32,'2026-11-23','11:42:45',NULL,'Presente','Entrada puntual autónoma (Turno Tarde)',1,'2026-11-23 15:42:45');
CREATE TABLE "asistencia_archivo" (
  "id_asistencia" INTEGER NOT NULL,
  "id_persona" INTEGER NOT NULL,
  "fecha" TEXT NOT NULL,
  "hora_entrada" TEXT,
  "hora_salida" TEXT,
  "estado" TEXT NOT NULL,
  "observaciones" TEXT NOT NULL,
  "id_usuario_registro" INTEGER,
  "fecha_archivo" TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id_asistencia"),
  FOREIGN KEY ("id_persona") REFERENCES "persona" ("id_persona") ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE "asistencia_curso" (
  "id_asistencia_curso" INTEGER PRIMARY KEY AUTOINCREMENT,
  "id_matricula" INTEGER NOT NULL,
  "id_cohorte" INTEGER NOT NULL,
  "id_persona" INTEGER NOT NULL,
  "fecha" TEXT NOT NULL,
  "hora" TEXT NOT NULL,
  "estado" TEXT NOT NULL DEFAULT 'Presente',
  "observaciones" TEXT DEFAULT '',
  "registrado_por" INTEGER,
  "created_at" TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY ("id_cohorte") REFERENCES "cohorte" ("id_cohorte") ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY ("id_matricula") REFERENCES "matricula" ("id_matricula") ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY ("id_persona") REFERENCES "persona" ("id_persona") ON DELETE CASCADE ON UPDATE CASCADE
);
INSERT INTO "asistencia_curso" VALUES(1,11,1,11,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(2,12,1,12,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(3,13,1,13,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(4,14,1,14,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(5,15,1,15,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(6,16,1,16,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(7,17,1,17,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(8,18,1,18,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(9,19,1,19,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(10,20,1,20,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(11,21,2,21,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(12,22,2,22,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(13,23,2,23,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(14,24,2,24,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(15,25,2,25,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(16,26,2,26,'2026-11-14','08:15:00','Retraso','Retraso justificado en llegada',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(17,27,2,27,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(18,28,2,28,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(19,29,3,29,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(20,30,3,30,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(21,31,3,31,'2026-11-14','08:15:00','Ausente','Inasistencia al taller sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(22,32,3,32,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(23,33,3,33,'2026-11-14','08:15:00','Retraso','Retraso justificado en llegada',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(24,34,3,34,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(25,35,3,35,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(26,36,3,36,'2026-11-14','08:15:00','Retraso','Retraso justificado en llegada',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(27,37,4,37,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(28,38,4,38,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(29,39,4,39,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(30,40,4,40,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(31,41,4,41,'2026-11-14','08:15:00','Ausente','Inasistencia al taller sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(32,42,4,42,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(33,43,4,43,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(34,44,4,44,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(35,45,5,45,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(36,46,5,46,'2026-11-14','08:15:00','Ausente','Inasistencia al taller sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(37,47,5,47,'2026-11-14','08:15:00','Retraso','Retraso justificado en llegada',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(38,48,5,48,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(39,49,5,49,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(40,50,5,50,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(41,51,6,51,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(42,52,6,52,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(43,53,6,53,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(44,54,6,54,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(45,55,6,55,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(46,56,6,56,'2026-11-14','08:15:00','Ausente','Inasistencia al taller sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(47,57,6,57,'2026-11-14','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(49,12,1,12,'2026-11-20','21:42:43','Presente','',2,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(50,13,1,13,'2026-11-20','15:08:58','Presente','',1,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(51,14,1,14,'2026-11-20','21:42:47','Presente','',2,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(52,15,1,15,'2026-11-20','21:42:41','Presente','',2,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(53,16,1,16,'2026-11-20','15:08:44','Ausente','',1,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(54,17,1,17,'2026-11-20','15:08:42','Ausente','',1,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(55,18,1,18,'2026-11-20','21:42:45','Presente','',2,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(56,19,1,19,'2026-11-20','21:42:44','Presente','',2,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(57,20,1,20,'2026-11-20','21:42:36','Ausente','',2,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(58,21,2,21,'2026-11-20','08:15:00','Retraso','Retraso justificado en llegada',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(59,22,2,22,'2026-11-20','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(60,23,2,23,'2026-11-20','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(61,24,2,24,'2026-11-20','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(62,25,2,25,'2026-11-20','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(63,26,2,26,'2026-11-20','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(64,27,2,27,'2026-11-20','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(65,28,2,28,'2026-11-20','08:15:00','Ausente','Inasistencia al taller sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(66,29,3,29,'2026-11-20','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(67,30,3,30,'2026-11-20','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(68,31,3,31,'2026-11-20','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(69,32,3,32,'2026-11-20','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(70,33,3,33,'2026-11-20','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(71,34,3,34,'2026-11-20','08:15:00','Ausente','Inasistencia al taller sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(72,35,3,35,'2026-11-20','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(73,36,3,36,'2026-11-20','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(74,37,4,37,'2026-11-20','08:15:00','Retraso','Retraso justificado en llegada',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(75,38,4,38,'2026-11-20','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(76,39,4,39,'2026-11-20','08:15:00','Ausente','Inasistencia al taller sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(77,40,4,40,'2026-11-20','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(78,41,4,41,'2026-11-20','08:15:00','Ausente','Inasistencia al taller sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(79,42,4,42,'2026-11-20','08:15:00','Ausente','Inasistencia al taller sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(80,43,4,43,'2026-11-20','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(81,44,4,44,'2026-11-20','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(82,45,5,45,'2026-11-20','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(83,46,5,46,'2026-11-20','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(84,47,5,47,'2026-11-20','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(85,48,5,48,'2026-11-20','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(86,49,5,49,'2026-11-20','08:15:00','Ausente','Inasistencia al taller sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(87,50,5,50,'2026-11-20','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(88,51,6,51,'2026-11-20','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(89,52,6,52,'2026-11-20','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(90,53,6,53,'2026-11-20','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(91,54,6,54,'2026-11-20','21:54:48','Retraso','',2,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(92,55,6,55,'2026-11-20','08:15:00','Ausente','Inasistencia al taller sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(93,56,6,56,'2026-11-20','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(94,57,6,57,'2026-11-20','08:15:00','Presente','Asistencia puntual a curso sabatino',3,'2026-11-20T14:36:52');
INSERT INTO "asistencia_curso" VALUES(120,20,1,20,'2026-11-06','19:12:26','Presente','Clase regular',4,'2026-11-20T19:06:15');
INSERT INTO "asistencia_curso" VALUES(121,20,1,20,'2026-11-13','19:12:26','Retraso','Llegó 15 min tarde',4,'2026-11-20T19:06:15');
INSERT INTO "asistencia_curso" VALUES(123,20,1,20,'2026-10-30','19:12:26','Ausente','Inasistencia 1',4,'2026-11-20T19:07:09');
INSERT INTO "asistencia_curso" VALUES(135,11,1,11,'2026-11-20','21:42:39','Retraso','',2,'2026-11-20T20:29:51');
INSERT INTO "asistencia_curso" VALUES(137,20,1,20,'2026-11-22','11:36:00','Justificado','Reposo médico por cuadro gripal severo [Soporte: Certificado Médico IVSS #89421]',4,'2026-11-22 15:35:30');
INSERT INTO "asistencia_curso" VALUES(139,20,1,20,'2026-11-01','11:36:00','Ausente','Inasistencia 1',4,'2026-11-22 15:36:00');
INSERT INTO "asistencia_curso" VALUES(140,20,1,20,'2026-11-08','11:36:00','Presente','Clase regular',4,'2026-11-22 15:36:01');
INSERT INTO "asistencia_curso" VALUES(141,20,1,20,'2026-11-15','11:36:00','Retraso','Llegó 15 min tarde',4,'2026-11-22 15:36:01');
CREATE TABLE "asistencia_historico" (
  "id_historico" INTEGER PRIMARY KEY AUTOINCREMENT,
  "id_persona" INTEGER NOT NULL,
  "anio" INTEGER NOT NULL,
  "mes" INTEGER NOT NULL,
  "total_asistencias" INTEGER NOT NULL DEFAULT '0',
  "total_ausencias" INTEGER NOT NULL DEFAULT '0',
  "total_retrasos" INTEGER NOT NULL DEFAULT '0',
  "total_salidas_tempranas" INTEGER NOT NULL DEFAULT '0',
  "total_dias_registrados" INTEGER NOT NULL DEFAULT '0',
  "fecha_cierre" TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "id_usuario_cierre" INTEGER,
  FOREIGN KEY ("id_persona") REFERENCES "persona" ("id_persona") ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY ("id_usuario_cierre") REFERENCES "usuario" ("id_usuario") ON DELETE CASCADE ON UPDATE CASCADE
);
INSERT INTO "asistencia_historico" VALUES(1,1,2026,11,1,0,0,0,1,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(2,2,2026,11,1,0,0,0,1,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(3,3,2026,11,1,0,0,0,1,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(4,4,2026,11,1,0,0,0,1,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(5,5,2026,11,1,0,0,0,1,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(6,6,2026,11,1,0,0,0,1,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(7,7,2026,11,1,0,0,0,1,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(8,8,2026,11,1,0,0,0,1,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(9,9,2026,11,1,0,0,0,1,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(10,11,2026,11,1,1,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(11,12,2026,11,2,0,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(12,13,2026,11,2,0,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(13,14,2026,11,1,0,1,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(14,15,2026,11,1,1,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(15,16,2026,11,2,0,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(16,17,2026,11,2,0,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(17,18,2026,11,2,0,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(18,19,2026,11,2,0,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(19,20,2026,11,2,0,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(20,21,2026,11,1,0,1,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(21,22,2026,11,2,0,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(22,23,2026,11,2,0,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(23,24,2026,11,2,0,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(24,25,2026,11,2,0,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(25,26,2026,11,1,0,1,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(26,27,2026,11,2,0,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(27,28,2026,11,1,1,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(28,29,2026,11,2,0,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(29,30,2026,11,2,0,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(30,31,2026,11,1,1,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(31,32,2026,11,2,0,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(32,33,2026,11,1,0,1,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(33,34,2026,11,1,1,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(34,35,2026,11,2,0,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(35,36,2026,11,1,0,1,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(36,37,2026,11,1,0,1,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(37,38,2026,11,2,0,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(38,39,2026,11,1,1,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(39,40,2026,11,2,0,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(40,41,2026,11,0,2,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(41,42,2026,11,1,1,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(42,43,2026,11,2,0,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(43,44,2026,11,2,0,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(44,45,2026,11,2,0,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(45,46,2026,11,1,1,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(46,47,2026,11,1,0,1,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(47,48,2026,11,2,0,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(48,49,2026,11,1,1,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(49,50,2026,11,2,0,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(50,51,2026,11,2,0,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(51,52,2026,11,2,0,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(52,53,2026,11,2,0,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(53,54,2026,11,1,1,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(54,55,2026,11,1,1,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(55,56,2026,11,1,1,0,0,2,'2026-11-22 20:45:39',1);
INSERT INTO "asistencia_historico" VALUES(56,57,2026,11,2,0,0,0,2,'2026-11-22 20:45:39',1);
CREATE TABLE "auditoria_ingresos" (
  "id_auditoria" INTEGER PRIMARY KEY AUTOINCREMENT,
  "id_usuario" INTEGER NOT NULL,
  "fecha_hora" TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "equipo" TEXT,
  FOREIGN KEY ("id_usuario") REFERENCES "usuario" ("id_usuario") ON DELETE CASCADE ON UPDATE CASCADE
);
INSERT INTO "auditoria_ingresos" VALUES(1,8,'2026-11-20T14:51:49','DESKTOP-AA1BH7G');
INSERT INTO "auditoria_ingresos" VALUES(2,1,'2026-11-20T21:37:49','DESKTOP-AA1BH7G');
INSERT INTO "auditoria_ingresos" VALUES(3,1,'2026-11-21T10:08:39','DESKTOP-AA1BH7G');
INSERT INTO "auditoria_ingresos" VALUES(4,1,'2026-11-21T13:14:34','DESKTOP-AA1BH7G');
INSERT INTO "auditoria_ingresos" VALUES(5,2,'2026-11-21T21:51:21','DESKTOP-AA1BH7G');
INSERT INTO "auditoria_ingresos" VALUES(6,2,'2026-11-21T22:52:51','DESKTOP-AA1BH7G');
INSERT INTO "auditoria_ingresos" VALUES(7,1,'2026-11-21T22:59:53','DESKTOP-AA1BH7G');
INSERT INTO "auditoria_ingresos" VALUES(8,1,'2026-11-22 19:58:30','DESKTOP-AA1BH7G');
INSERT INTO "auditoria_ingresos" VALUES(9,1,'2026-11-22 21:44:22','DESKTOP-AA1BH7G');
INSERT INTO "auditoria_ingresos" VALUES(10,1,'2026-11-22 22:28:14','DESKTOP-AA1BH7G');
INSERT INTO "auditoria_ingresos" VALUES(11,1,'2026-11-23 16:06:19','DESKTOP-AA1BH7G');
INSERT INTO "auditoria_ingresos" VALUES(12,2,'2026-11-23 16:07:42','DESKTOP-AA1BH7G');
CREATE TABLE "bitacora_asistencia" (
  "id_bitacora" INTEGER PRIMARY KEY AUTOINCREMENT,
  "id_asistencia_curso" INTEGER,
  "id_matricula" INTEGER,
  "id_persona" INTEGER NOT NULL,
  "id_cohorte" INTEGER NOT NULL,
  "fecha_asistencia" TEXT NOT NULL,
  "estado_anterior" TEXT,
  "estado_nuevo" TEXT NOT NULL,
  "accion" TEXT NOT NULL,
  "id_usuario_operador" INTEGER,
  "nombre_operador" TEXT NOT NULL DEFAULT 'Sistema',
  "rol_operador" TEXT NOT NULL DEFAULT 'Sistema',
  "ip_origen" TEXT,
  "fecha_operacion" TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "observaciones" TEXT
);
INSERT INTO "bitacora_asistencia" VALUES(1,48,11,11,1,'2026-11-20','Ausente','Presente','MODIFICACION',1,'Carmen Morales','Directivo','127.0.0.1','2026-11-20T18:04:42','Prueba Unitaria Auditoría');
INSERT INTO "bitacora_asistencia" VALUES(2,48,11,11,1,'2026-11-20','Presente','Presente','MODIFICACION',1,'Carmen Morales','Directivo','127.0.0.1','2026-11-20T18:11:16','Prueba Unitaria Auditoría');
INSERT INTO "bitacora_asistencia" VALUES(3,57,20,20,1,'2026-11-20','Retraso','Presente','MODIFICACION',1,'Carmen Morales','Directivo',NULL,'2026-11-20T18:36:05','Primer escaneo QR');
INSERT INTO "bitacora_asistencia" VALUES(4,57,20,20,1,'2026-11-20','Presente','Presente','MODIFICACION',1,'Carmen Morales','Directivo',NULL,'2026-11-20T18:36:06','Re-escaneo carnet');
INSERT INTO "bitacora_asistencia" VALUES(5,120,20,20,1,'2026-11-06',NULL,'Presente','REGISTRO_INICIAL',4,'Alejandro José Navarro Rivas','Docente',NULL,'2026-11-20T19:06:15','Clase regular');
INSERT INTO "bitacora_asistencia" VALUES(6,121,20,20,1,'2026-11-13',NULL,'Retraso','REGISTRO_INICIAL',4,'Alejandro José Navarro Rivas','Docente',NULL,'2026-11-20T19:06:15','Llegó 15 min tarde');
INSERT INTO "bitacora_asistencia" VALUES(7,57,20,20,1,'2026-11-20','Presente','Ausente','MODIFICACION',4,'Alejandro José Navarro Rivas','Docente',NULL,'2026-11-20T19:06:16','Falta no justificada aún');
INSERT INTO "bitacora_asistencia" VALUES(8,123,20,20,1,'2026-10-30',NULL,'Ausente','REGISTRO_INICIAL',4,'Alejandro José Navarro Rivas','Docente',NULL,'2026-11-20T19:07:09','Inasistencia 1');
INSERT INTO "bitacora_asistencia" VALUES(9,120,20,20,1,'2026-11-06','Presente','Presente','MODIFICACION',4,'Alejandro José Navarro Rivas','Docente',NULL,'2026-11-20T19:07:09','Clase regular');
INSERT INTO "bitacora_asistencia" VALUES(10,121,20,20,1,'2026-11-13','Retraso','Retraso','MODIFICACION',4,'Alejandro José Navarro Rivas','Docente',NULL,'2026-11-20T19:07:09','Llegó 15 min tarde');
INSERT INTO "bitacora_asistencia" VALUES(11,57,20,20,1,'2026-11-20','Ausente','Ausente','MODIFICACION',4,'Alejandro José Navarro Rivas','Docente',NULL,'2026-11-20T19:07:10','Falta no justificada aún');
INSERT INTO "bitacora_asistencia" VALUES(12,123,20,20,1,'2026-10-30','Ausente','Ausente','MODIFICACION',4,'Alejandro José Navarro Rivas','Docente',NULL,'2026-11-20T19:09:46','Inasistencia 1');
INSERT INTO "bitacora_asistencia" VALUES(13,120,20,20,1,'2026-11-06','Presente','Presente','MODIFICACION',4,'Alejandro José Navarro Rivas','Docente',NULL,'2026-11-20T19:09:47','Clase regular');
INSERT INTO "bitacora_asistencia" VALUES(14,121,20,20,1,'2026-11-13','Retraso','Retraso','MODIFICACION',4,'Alejandro José Navarro Rivas','Docente',NULL,'2026-11-20T19:09:47','Llegó 15 min tarde');
INSERT INTO "bitacora_asistencia" VALUES(15,57,20,20,1,'2026-11-20','Justificado','Ausente','MODIFICACION',4,'Alejandro José Navarro Rivas','Docente',NULL,'2026-11-20T19:09:47','Falta no justificada aún');
INSERT INTO "bitacora_asistencia" VALUES(16,57,20,20,1,'2026-11-20','Ausente','Justificado','JUSTIFICACION',NULL,'Sistema','Sistema',NULL,'2026-11-20T19:09:48','Reposo médico por cuadro gripal severo [Soporte: Certificado Médico IVSS #89421]');
INSERT INTO "bitacora_asistencia" VALUES(17,123,20,20,1,'2026-10-30','Ausente','Ausente','MODIFICACION',4,'Alejandro José Navarro Rivas','Docente',NULL,'2026-11-20T19:12:26','Inasistencia 1');
INSERT INTO "bitacora_asistencia" VALUES(18,120,20,20,1,'2026-11-06','Presente','Presente','MODIFICACION',4,'Alejandro José Navarro Rivas','Docente',NULL,'2026-11-20T19:12:26','Clase regular');
INSERT INTO "bitacora_asistencia" VALUES(19,121,20,20,1,'2026-11-13','Retraso','Retraso','MODIFICACION',4,'Alejandro José Navarro Rivas','Docente',NULL,'2026-11-20T19:12:26','Llegó 15 min tarde');
INSERT INTO "bitacora_asistencia" VALUES(20,57,20,20,1,'2026-11-20','Justificado','Ausente','MODIFICACION',4,'Alejandro José Navarro Rivas','Docente',NULL,'2026-11-20T19:12:27','Falta no justificada aún');
INSERT INTO "bitacora_asistencia" VALUES(21,57,20,20,1,'2026-11-20','Ausente','Justificado','JUSTIFICACION',NULL,'Sistema','Sistema',NULL,'2026-11-20T19:12:27','Reposo médico por cuadro gripal severo [Soporte: Certificado Médico IVSS #89421]');
INSERT INTO "bitacora_asistencia" VALUES(22,135,11,11,1,'2026-11-20',NULL,'Presente','REGISTRO_INICIAL',4,'Alejandro José Navarro Rivas','Docente',NULL,'2026-11-20T20:29:51','Prueba Módulo 5');
INSERT INTO "bitacora_asistencia" VALUES(23,135,11,11,1,'2026-11-20','Presente','Presente','MODIFICACION',4,'Alejandro José Navarro Rivas','Docente',NULL,'2026-11-20T20:29:52','Prueba Módulo 5');
INSERT INTO "bitacora_asistencia" VALUES(24,135,11,11,1,'2026-11-20','Ausente','Justificado','JUSTIFICACION',NULL,'Sistema','Sistema',NULL,'2026-11-20T20:29:52','Permiso médico comprobado para prueba de auditoría [Soporte: Certificado_Medico_Test.pdf]');
INSERT INTO "bitacora_asistencia" VALUES(25,136,11,11,1,'2026-11-22',NULL,'Presente','REGISTRO_INICIAL',1,'Carmen Morales','Directivo','127.0.0.1','2026-11-22 15:35:02','Prueba Unitaria Auditoría');
INSERT INTO "bitacora_asistencia" VALUES(26,137,20,20,1,'2026-11-22',NULL,'Presente','REGISTRO_INICIAL',1,'Carmen Morales','Directivo',NULL,'2026-11-22 15:35:30','Primer escaneo QR');
INSERT INTO "bitacora_asistencia" VALUES(27,137,20,20,1,'2026-11-22','Presente','Presente','MODIFICACION',1,'Carmen Morales','Directivo',NULL,'2026-11-22 15:35:30','Re-escaneo carnet');
INSERT INTO "bitacora_asistencia" VALUES(28,139,20,20,1,'2026-11-01',NULL,'Ausente','REGISTRO_INICIAL',4,'Alejandro José Navarro Rivas','Docente',NULL,'2026-11-22 15:36:01','Inasistencia 1');
INSERT INTO "bitacora_asistencia" VALUES(29,140,20,20,1,'2026-11-08',NULL,'Presente','REGISTRO_INICIAL',4,'Alejandro José Navarro Rivas','Docente',NULL,'2026-11-22 15:36:01','Clase regular');
INSERT INTO "bitacora_asistencia" VALUES(30,141,20,20,1,'2026-11-15',NULL,'Retraso','REGISTRO_INICIAL',4,'Alejandro José Navarro Rivas','Docente',NULL,'2026-11-22 15:36:01','Llegó 15 min tarde');
INSERT INTO "bitacora_asistencia" VALUES(31,137,20,20,1,'2026-11-22','Presente','Ausente','MODIFICACION',4,'Alejandro José Navarro Rivas','Docente',NULL,'2026-11-22 15:36:01','Falta no justificada aún');
INSERT INTO "bitacora_asistencia" VALUES(32,137,20,20,1,'2026-11-22','Ausente','Justificado','JUSTIFICACION',NULL,'Sistema','Sistema',NULL,'2026-11-22 15:36:01','Reposo médico por cuadro gripal severo [Soporte: Certificado Médico IVSS #89421]');
CREATE TABLE "cierre_diario" (
  "id_cierre_diario" INTEGER PRIMARY KEY AUTOINCREMENT,
  "fecha" TEXT NOT NULL UNIQUE,
  "total_matricula" INTEGER NOT NULL DEFAULT '0',
  "presentes" INTEGER NOT NULL DEFAULT '0',
  "retrasos" INTEGER NOT NULL DEFAULT '0',
  "salidas_tempranas" INTEGER NOT NULL DEFAULT '0',
  "ausencias" INTEGER NOT NULL DEFAULT '0',
  "justificados" INTEGER NOT NULL DEFAULT '0',
  "pct_asistencia" REAL NOT NULL DEFAULT '0.00',
  "archivo_pdf" TEXT,
  "archivo_excel" TEXT,
  "id_usuario_cierre" INTEGER,
  "creado_en" TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY ("id_usuario_cierre") REFERENCES "usuario" ("id_usuario") ON DELETE CASCADE ON UPDATE CASCADE
);
INSERT INTO "cierre_diario" VALUES(1,'2026-11-22',58,0,0,0,0,1,1.72,'C:\Users\vanes\OneDrive\Desktop\Asista_Sistema\asista\respaldos\cierres_diarios\pdf\cierre_diario_2026_11_22.pdf','C:\Users\vanes\OneDrive\Desktop\Asista_Sistema\asista\respaldos\cierres_diarios\excel\cierre_diario_2026_11_22.xlsx',1,'2026-11-22 20:09:03');
CREATE TABLE "cierre_mensual" (
  "id_cierre" INTEGER PRIMARY KEY AUTOINCREMENT,
  "anio" INTEGER NOT NULL,
  "mes" INTEGER NOT NULL,
  "fecha_cierre" TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "total_personas" INTEGER NOT NULL DEFAULT '0',
  "archivado" INTEGER NOT NULL DEFAULT '0',
  "id_usuario_cierre" INTEGER,
  FOREIGN KEY ("id_usuario_cierre") REFERENCES "usuario" ("id_usuario") ON DELETE CASCADE ON UPDATE CASCADE
);
INSERT INTO "cierre_mensual" VALUES(1,2026,11,'2026-11-22 20:45:40',56,0,1);
CREATE TABLE "cohorte" (
  "id_cohorte" INTEGER PRIMARY KEY AUTOINCREMENT,
  "id_curso" INTEGER NOT NULL,
  "id_periodo" INTEGER NOT NULL,
  "id_docente" INTEGER,
  "nombre_grupo" TEXT NOT NULL,
  "dias_semana" TEXT NOT NULL,
  "hora_inicio" TEXT NOT NULL,
  "hora_fin" TEXT NOT NULL,
  "aula" TEXT DEFAULT 'Aula Principal',
  "cupo_maximo" INTEGER NOT NULL DEFAULT '30',
  "estado" TEXT NOT NULL DEFAULT 'Inscripciones',
  "created_at" TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY ("id_curso") REFERENCES "curso" ("id_curso") ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY ("id_docente") REFERENCES "persona" ("id_persona") ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY ("id_periodo") REFERENCES "periodo" ("id_periodo") ON DELETE CASCADE ON UPDATE CASCADE
);
INSERT INTO "cohorte" VALUES(1,1,1,3,'Sábado Mañana (08:00 - 12:00)','Sábados','08:00:00','12:00:00','Laboratorio de Computación 1',20,'En Curso','2026-11-20T14:36:51');
INSERT INTO "cohorte" VALUES(2,2,1,5,'Sábado Tarde (13:00 - 17:00)','Sábados','13:00:00','17:00:00','Taller de Mantenimiento',15,'En Curso','2026-11-20T14:36:51');
INSERT INTO "cohorte" VALUES(3,3,1,4,'Sábado Mañana (08:00 - 12:00)','Sábados','08:00:00','12:00:00','Aula Multimedia 2',18,'En Curso','2026-11-20T14:36:51');
INSERT INTO "cohorte" VALUES(4,4,1,2,'Sábado Mañana (08:00 - 12:00)','Sábados','08:00:00','12:00:00','Aula 4 de Formación',16,'En Curso','2026-11-20T14:36:51');
INSERT INTO "cohorte" VALUES(5,5,1,3,'Sábado Tarde (13:00 - 17:00)','Sábados','13:00:00','17:00:00','Laboratorio de Robótica',14,'En Curso','2026-11-20T14:36:51');
INSERT INTO "cohorte" VALUES(6,6,1,5,'Sábado Tarde (13:00 - 17:00)','Sábados','13:00:00','17:00:00','Taller de Electricidad',15,'En Curso','2026-11-20T14:36:51');
CREATE TABLE "configuracion_institucional" (
  "clave" TEXT NOT NULL,
  "valor" TEXT NOT NULL,
  "descripcion" TEXT,
  PRIMARY KEY ("clave")
);
INSERT INTO "configuracion_institucional" VALUES('hora_entrada_manana','07:10','Hora límite de entrada para el Turno Mañana');
INSERT INTO "configuracion_institucional" VALUES('hora_entrada_tarde','12:45','Hora límite de entrada para el Turno Tarde');
INSERT INTO "configuracion_institucional" VALUES('hora_salida_manana','11:30','Hora mínima de salida para el Turno Mañana');
INSERT INTO "configuracion_institucional" VALUES('hora_salida_tarde','17:30','Hora mínima de salida para el Turno Tarde');
INSERT INTO "configuracion_institucional" VALUES('nombre_institucion','Unidad Educativa Prof. Aristóbulo Istúriz','Nombre oficial de la institución');
INSERT INTO "configuracion_institucional" VALUES('tolerancia_minutos','20','Minutos de cortesía/tolerancia');
CREATE TABLE "curso" (
  "id_curso" INTEGER PRIMARY KEY AUTOINCREMENT,
  "codigo" TEXT NOT NULL UNIQUE,
  "nombre" TEXT NOT NULL,
  "descripcion" TEXT,
  "duracion_semanas" INTEGER NOT NULL DEFAULT '12',
  "activo" INTEGER NOT NULL DEFAULT '1',
  "created_at" TEXT DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO "curso" VALUES(1,'INF-101','Computación y Ofimática Comunitaria','Manejo integral de herramientas ofimáticas, internet y productividad digital para jóvenes y adultos.',16,1,'2026-11-20T14:36:51');
INSERT INTO "curso" VALUES(2,'TEC-102','Mantenimiento y Reparación de Computadoras','Diagnóstico de hardware, ensamble, instalación de software y mantenimiento preventivo/correctivo.',16,1,'2026-11-20T14:36:51');
INSERT INTO "curso" VALUES(3,'DIS-201','Diseño Gráfico y Marketing Digital','Diseño visual, creación de marca, edición fotográfica y manejo estratégico de redes sociales para emprendimientos.',16,1,'2026-11-20T14:36:51');
INSERT INTO "curso" VALUES(4,'ADM-202','Contabilidad Práctica y Tributación','Nociones contables, libro diario, balances y gestión tributaria SENIAT para pequeños comerciantes y emprendedores.',16,1,'2026-11-20T14:36:51');
INSERT INTO "curso" VALUES(5,'ROB-301','Robótica y Automatización','Fundamentos de electrónica, placas programables, sensores y proyectos de automatización.',16,1,'2026-11-20T14:36:51');
INSERT INTO "curso" VALUES(6,'ELE-103','Electricidad Básica y Residencial','Circuitos eléctricos, normas de seguridad, tableros residenciales e instalaciones comunitarias.',16,1,'2026-11-20T14:36:51');
CREATE TABLE "estudiante" (
  "id_estudiante" INTEGER PRIMARY KEY AUTOINCREMENT,
  "id_persona" INTEGER NOT NULL UNIQUE,
  "id_seccion" INTEGER NOT NULL,
  "fecha_ingreso" TEXT,
  "representante" TEXT,
  "telefono_representante" TEXT,
  FOREIGN KEY ("id_persona") REFERENCES "persona" ("id_persona") ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY ("id_seccion") REFERENCES "seccion" ("id_seccion") ON DELETE CASCADE ON UPDATE CASCADE
);
INSERT INTO "estudiante" VALUES(11,11,1,NULL,'15 años (Joven bachiller)',NULL);
INSERT INTO "estudiante" VALUES(12,12,1,NULL,'12 años',NULL);
INSERT INTO "estudiante" VALUES(13,13,1,NULL,'17 años (Joven bachiller)',NULL);
INSERT INTO "estudiante" VALUES(14,14,1,NULL,'18 años (Joven estudiante)',NULL);
INSERT INTO "estudiante" VALUES(15,15,1,NULL,'19 años (Universitario)',NULL);
INSERT INTO "estudiante" VALUES(16,16,1,NULL,'14',NULL);
INSERT INTO "estudiante" VALUES(17,17,1,NULL,'24 años (Comercio local)',NULL);
INSERT INTO "estudiante" VALUES(18,18,1,NULL,'27 años (Emprendedora)',NULL);
INSERT INTO "estudiante" VALUES(19,19,1,NULL,'32 años (Técnico independiente)',NULL);
INSERT INTO "estudiante" VALUES(20,20,1,NULL,'43 años',NULL);
INSERT INTO "estudiante" VALUES(21,21,2,NULL,'15 años (Joven técnico)',NULL);
INSERT INTO "estudiante" VALUES(22,22,2,NULL,'16 años (Joven técnico)',NULL);
INSERT INTO "estudiante" VALUES(23,23,2,NULL,'18 años (Bachiller)',NULL);
INSERT INTO "estudiante" VALUES(24,24,2,NULL,'20 años (Universitario)',NULL);
INSERT INTO "estudiante" VALUES(25,25,2,NULL,'23 años (Técnico de soporte)',NULL);
INSERT INTO "estudiante" VALUES(26,26,2,NULL,'28 años (Emprendedor servicios)',NULL);
INSERT INTO "estudiante" VALUES(27,27,2,NULL,'34 años (Independiente)',NULL);
INSERT INTO "estudiante" VALUES(28,28,2,NULL,'45 años (Comunidad Cabimas)',NULL);
INSERT INTO "estudiante" VALUES(29,29,3,NULL,'15 años (Joven creativa)',NULL);
INSERT INTO "estudiante" VALUES(30,30,3,NULL,'16 años (Joven estudiante)',NULL);
INSERT INTO "estudiante" VALUES(31,31,3,NULL,'18 años (Bachiller)',NULL);
INSERT INTO "estudiante" VALUES(32,32,1,NULL,'20 años (Comunity manager)',NULL);
INSERT INTO "estudiante" VALUES(33,33,3,NULL,'22 años (Diseñadora junior)',NULL);
INSERT INTO "estudiante" VALUES(34,34,3,NULL,'25 años (Emprendedora repostería)',NULL);
INSERT INTO "estudiante" VALUES(35,35,3,NULL,'30 años (Fotógrafo independiente)',NULL);
INSERT INTO "estudiante" VALUES(36,36,3,NULL,'41 años (Comercio confección)',NULL);
INSERT INTO "estudiante" VALUES(37,37,4,NULL,'15 años (Joven estudiante)',NULL);
INSERT INTO "estudiante" VALUES(38,38,4,NULL,'17 años (Joven bachiller)',NULL);
INSERT INTO "estudiante" VALUES(39,39,4,NULL,'19 años (Universitario adm)',NULL);
INSERT INTO "estudiante" VALUES(40,40,4,NULL,'21 años (Auxiliar contable)',NULL);
INSERT INTO "estudiante" VALUES(41,41,4,NULL,'26 años (Dueño de bodega)',NULL);
INSERT INTO "estudiante" VALUES(42,42,4,NULL,'33 años (Emprendedora víveres)',NULL);
INSERT INTO "estudiante" VALUES(43,43,4,NULL,'44 años (Comerciante)',NULL);
INSERT INTO "estudiante" VALUES(44,44,4,NULL,'51 años (Comunidad Cabimas)',NULL);
INSERT INTO "estudiante" VALUES(45,45,5,NULL,'15 años (Joven entusiasta)',NULL);
INSERT INTO "estudiante" VALUES(46,46,5,NULL,'16 años (Joven técnico)',NULL);
INSERT INTO "estudiante" VALUES(47,47,5,NULL,'14 años',NULL);
INSERT INTO "estudiante" VALUES(48,48,5,NULL,'20 años (Estudiante ingeniería)',NULL);
INSERT INTO "estudiante" VALUES(49,49,5,NULL,'23 años (Técnico electricista)',NULL);
INSERT INTO "estudiante" VALUES(50,50,5,NULL,'29 años (Técnico industrial)',NULL);
INSERT INTO "estudiante" VALUES(51,51,6,NULL,'15 años (Joven aprendiz)',NULL);
INSERT INTO "estudiante" VALUES(52,52,6,NULL,'17 años (Joven aprendiz)',NULL);
INSERT INTO "estudiante" VALUES(53,53,6,NULL,'19 años (Ayudante técnico)',NULL);
INSERT INTO "estudiante" VALUES(54,54,6,NULL,'21 años (Instalador)',NULL);
INSERT INTO "estudiante" VALUES(55,55,6,NULL,'28 años (Oficio electricidad)',NULL);
INSERT INTO "estudiante" VALUES(56,56,6,NULL,'36 años (Comunidad Cabimas)',NULL);
INSERT INTO "estudiante" VALUES(57,57,6,NULL,'47 años (Trabajador independiente)',NULL);
CREATE TABLE "matricula" (
  "id_matricula" INTEGER PRIMARY KEY AUTOINCREMENT,
  "id_persona" INTEGER NOT NULL,
  "id_cohorte" INTEGER NOT NULL,
  "fecha_inscripcion" TEXT NOT NULL,
  "estado" TEXT NOT NULL DEFAULT 'En Curso',
  "porcentaje_asistencia" REAL NOT NULL DEFAULT '0.00',
  "observaciones" TEXT,
  "created_at" TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY ("id_cohorte") REFERENCES "cohorte" ("id_cohorte") ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY ("id_persona") REFERENCES "persona" ("id_persona") ON DELETE CASCADE ON UPDATE CASCADE
);
INSERT INTO "matricula" VALUES(11,11,1,'2026-01-10','En Curso',100.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(12,12,1,'2026-01-10','En Curso',100.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(13,13,1,'2026-01-10','En Curso',100.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(14,14,1,'2026-01-10','En Curso',100.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(15,15,1,'2026-01-10','En Curso',100.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(16,16,1,'2026-01-10','En Curso',50.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(17,17,1,'2026-01-10','En Curso',50.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(18,18,1,'2026-01-10','En Curso',100.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(19,19,1,'2026-01-10','En Curso',100.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(20,20,1,'2026-01-10','En Curso',66.67,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(21,21,2,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(22,22,2,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(23,23,2,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(24,24,2,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(25,25,2,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(26,26,2,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(27,27,2,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(28,28,2,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(29,29,3,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(30,30,3,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(31,31,3,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(32,32,3,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(33,33,3,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(34,34,3,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(35,35,3,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(36,36,3,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(37,37,4,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(38,38,4,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(39,39,4,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(40,40,4,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(41,41,4,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(42,42,4,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(43,43,4,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(44,44,4,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(45,45,5,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(46,46,5,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(47,47,5,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(48,48,5,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(49,49,5,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(50,50,5,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(51,51,6,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(52,52,6,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(53,53,6,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(54,54,6,'2026-01-10','En Curso',100.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(55,55,6,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(56,56,6,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
INSERT INTO "matricula" VALUES(57,57,6,'2026-01-10','En Curso',0.0,NULL,'2026-11-20T14:36:52');
CREATE TABLE "periodo" (
  "id_periodo" INTEGER PRIMARY KEY AUTOINCREMENT,
  "nombre" TEXT NOT NULL,
  "codigo" TEXT NOT NULL UNIQUE,
  "fecha_inicio" TEXT NOT NULL,
  "fecha_fin" TEXT NOT NULL,
  "estado" TEXT NOT NULL DEFAULT 'Activo',
  "created_at" TEXT DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO "periodo" VALUES(1,'Capacitación Sabatina 2026','SAB-2026','2026-01-10','2026-07-25','Activo','2026-11-20T14:36:51');
CREATE TABLE "persona" (
  "id_persona" INTEGER PRIMARY KEY AUTOINCREMENT,
  "cedula" TEXT NOT NULL UNIQUE,
  "nombre" TEXT NOT NULL,
  "apellido" TEXT NOT NULL,
  "telefono" TEXT,
  "tipo_persona" TEXT NOT NULL,
  "activo" INTEGER NOT NULL DEFAULT '1',
  "fecha_inactivo" TEXT,
  "motivo_inactivo" TEXT,
  "foto" TEXT,
  "created_at" TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO "persona" VALUES(1,'12456789','Carmen Elena','Morales de Istúriz','0414-7890123','Personal',1,NULL,NULL,NULL,'2026-11-20T14:36:51');
INSERT INTO "persona" VALUES(2,'14123456','Roberto Carlos','Méndez Peña','0412-4567890','Personal',1,NULL,NULL,NULL,'2026-11-20T14:36:51');
INSERT INTO "persona" VALUES(3,'16789012','Alejandro José','Navarro Rivas','0424-6789012','Personal',1,NULL,NULL,NULL,'2026-11-20T14:36:51');
INSERT INTO "persona" VALUES(4,'17654321','Mariana Beatriz','Silva González','0414-8901234','Personal',1,NULL,NULL,NULL,'2026-11-20T14:36:51');
INSERT INTO "persona" VALUES(5,'18234567','Carlos Eduardo','Gutiérrez León','0412-9012345','Personal',1,NULL,NULL,NULL,'2026-11-20T14:36:51');
INSERT INTO "persona" VALUES(6,'19876543','Patricia Carolina','Rivas Zambrano','0424-1234567','Personal',1,NULL,NULL,NULL,'2026-11-20T14:36:51');
INSERT INTO "persona" VALUES(7,'20345678','Yuleidys Coromoto','Delgado Ferrer','0416-2345678','Personal',1,NULL,NULL,NULL,'2026-11-20T14:36:51');
INSERT INTO "persona" VALUES(8,'15987654','José Gregorio','Colina Suárez','0414-3456789','Personal',1,NULL,NULL,NULL,'2026-11-20T14:36:51');
INSERT INTO "persona" VALUES(9,'13567890','Ramón Antonio','Castillo Pineda','0412-5678901','Personal',1,NULL,NULL,NULL,'2026-11-20T14:36:51');
INSERT INTO "persona" VALUES(11,'31456123','Kevin Jesús','Chirinos Morán','0412-1110001','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(12,'30987654','Andrea Valentina','León Parra','0424-1110002','Estudiante',1,NULL,NULL,'30987654.jpg','2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(13,'30123987','Gabriel Antonio','Sánchez Pérez','0414-1110003','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(14,'29654123','Daniela Carolina','Reyes Villalobos','0416-1110004','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(15,'28765432','Luis Fernando','Gómez Finol','0412-1110005','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(16,'27345678','María Alejandra','Bracho Nava','0424-1110006','Estudiante',1,NULL,NULL,'27345678.jpg','2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(17,'25987123','José Manuel','Camacho Quintero','0414-1110007','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(18,'24567890','Yusmary Coromoto','Pineda Rincón','0416-1110008','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(19,'22345678','Carlos Alberto','Medina Suárez','0412-1110009','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(20,'19876541','Gladys Elena','Alvarado de Díaz','0414-1110010','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(21,'31234567','Sebastián David','Urdaneta Ferrer','0424-2220001','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(22,'30456789','Jesús Enrique','Torres Benítez','0414-2220002','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(23,'29876543','Alejandro José','Vargas Colmenares','0412-2220003','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(24,'28123456','Jorge Luis','Montiel Barboza','0416-2220004','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(25,'26789012','David Eduardo','Paredes Rivas','0424-2220005','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(26,'24321098','Reinaldo Andrés','Morillo Castillo','0414-2220006','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(27,'21456789','Edgar Antonio','López Hurtado','0412-2220007','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(28,'18765432','Franklin José','Ríos Bermúdez','0416-2220008','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(29,'31567890','Camila Sofía','Naveda Pirela','0414-3330001','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(30,'30678901','Valeria Nicole','Paz Henríquez','0412-3330002','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(31,'29456789','Adriana Paola','Guerrero Bravo','0424-3330003','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(32,'28456123','Mauricio José','Rondón Marcano','0416-3330004','Estudiante',1,NULL,NULL,'28456123.jpg','2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(33,'27123456','Stefany Coromoto','Chávez Romero','0414-3330005','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(34,'25678901','Bárbara Patricia','Salas Mendoza','0412-3330006','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(35,'23456789','Gustavo Adolfo','Prieto Carrasquero','0424-3330007','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(36,'20123456','Maritza Beatriz','Vilchez de Rincón','0416-3330008','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(37,'31890123','Diana Marcela','Osorio Fuentes','0412-4440001','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(38,'30345678','Mariangel Cristina','Puerta Godoy','0414-4440002','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(39,'29123456','José Gregorio','Acosta Semprún','0424-4440003','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(40,'27654321','Roxana Carolina','Duarte Briceño','0416-4440004','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(41,'25123456','Néstor Enrique','Quintero Ávila','0412-4440005','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(42,'22987654','Beatriz Eugenia','Vera Cardozo','0414-4440006','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(43,'19456789','Ana María','Suárez de González','0424-4440007','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(44,'17234567','Héctor Ramón','Padrón Rosales','0416-4440008','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(45,'31901234','Diego Alejandro','Pérez Molero','0424-5550001','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(46,'30789012','Manuel Ricardo','Zambrano Silva','0412-5550002','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(47,'29567890','Leonardo Fabio','Mendoza Valbuena','0414-5550003','Estudiante',1,NULL,NULL,'29567890.jpg','2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(48,'28234567','Christian Paul','Carrizo Delgado','0416-5550004','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(49,'26890123','Guillermo José','Sarmiento Chacín','0424-5550005','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(50,'23678901','Rubén Darío','Escobar Montero','0412-5550006','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(51,'31012345','Anthony José','Márquez Perozo','0414-6660001','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(52,'30234567','Eduardo Daniel','Rangel Bastidas','0416-6660002','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(53,'29345678','Víctor Hugo','Castillo Palmar','0412-6660003','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(54,'27890123','Ángel David','Pacheco Guerra','0424-6660004','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(55,'24890123','Wuilmer Jesús','Ortiz Cárdenas','0414-6660005','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(56,'21765432','Alirio José','Fernández Medina','0412-6660006','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(57,'18345678','Oswaldo Enrique','Montilla Leal','0416-6660007','Estudiante',1,NULL,NULL,NULL,'2026-11-20T14:36:52');
INSERT INTO "persona" VALUES(58,'30653899','Vanessa','Morales',NULL,'Personal',1,NULL,NULL,NULL,'2026-11-20T14:51:26');
INSERT INTO "persona" VALUES(59,'11222333','Carmen','Morales',NULL,'Personal',1,NULL,NULL,NULL,'2026-11-20T17:46:33');
CREATE TABLE "personal" (
  "id_personal" INTEGER PRIMARY KEY AUTOINCREMENT,
  "id_persona" INTEGER NOT NULL UNIQUE,
  "cargo" TEXT NOT NULL,
  "fecha_ingreso" TEXT,
  FOREIGN KEY ("id_persona") REFERENCES "persona" ("id_persona") ON DELETE CASCADE ON UPDATE CASCADE
);
INSERT INTO "personal" VALUES(1,1,'Directivo','2018-09-01');
INSERT INTO "personal" VALUES(2,2,'Docente','2020-01-15');
INSERT INTO "personal" VALUES(3,3,'Docente','2021-09-15');
INSERT INTO "personal" VALUES(4,4,'Docente','2022-02-01');
INSERT INTO "personal" VALUES(5,5,'Docente','2021-10-01');
INSERT INTO "personal" VALUES(6,6,'Administrativo','2022-09-15');
INSERT INTO "personal" VALUES(7,7,'Administrativo','2023-01-10');
INSERT INTO "personal" VALUES(8,8,'Vigilante','2019-05-20');
INSERT INTO "personal" VALUES(9,9,'Obrero','2018-10-15');
INSERT INTO "personal" VALUES(10,58,'Directivo',NULL);
INSERT INTO "personal" VALUES(11,59,'Directivo',NULL);
CREATE TABLE "seccion" (
  "id_seccion" INTEGER PRIMARY KEY AUTOINCREMENT,
  "grado_ano" INTEGER NOT NULL,
  "seccion_letra" TEXT NOT NULL,
  "turno" TEXT NOT NULL,
  "n_estudiantes" INTEGER NOT NULL DEFAULT '0'
);
INSERT INTO "seccion" VALUES(1,1,'Computación Comunitaria','Sábado Mañana',25);
INSERT INTO "seccion" VALUES(2,2,'Reparación de PC','Sábado Tarde',20);
INSERT INTO "seccion" VALUES(3,3,'Diseño Gráfico & Marketing','Sábado Mañana',22);
INSERT INTO "seccion" VALUES(4,4,'Contabilidad Práctica','Sábado Mañana',20);
INSERT INTO "seccion" VALUES(5,5,'Robótica & Automatización','Sábado Tarde',16);
INSERT INTO "seccion" VALUES(6,6,'Electricidad Residencial','Sábado Tarde',19);
CREATE TABLE "sesion_clase" (
  "id_sesion" INTEGER PRIMARY KEY AUTOINCREMENT,
  "id_cohorte" INTEGER NOT NULL,
  "fecha" TEXT NOT NULL,
  "hora_apertura" TEXT,
  "hora_cierre" TEXT,
  "id_docente" INTEGER,
  "total_presentes" INTEGER DEFAULT '0',
  "total_ausentes" INTEGER DEFAULT '0',
  "total_retrasos" INTEGER DEFAULT '0',
  "total_justificados" INTEGER DEFAULT '0',
  "estado" TEXT DEFAULT 'Abierta',
  "firma_docente" TEXT,
  FOREIGN KEY ("id_cohorte") REFERENCES "cohorte" ("id_cohorte") ON DELETE CASCADE ON UPDATE CASCADE
);
INSERT INTO "sesion_clase" VALUES(1,1,'2026-11-20','08:00:00','21:42:57',4,6,3,1,0,'Cerrada','Juan Lopez');
INSERT INTO "sesion_clase" VALUES(2,2,'2026-11-20','13:00:00',NULL,5,7,1,0,0,'Abierta','Carlos Gutiérrez');
INSERT INTO "sesion_clase" VALUES(3,3,'2026-11-20','08:00:00',NULL,4,7,0,1,0,'Abierta','Mariana Silva');
INSERT INTO "sesion_clase" VALUES(4,4,'2026-11-20','08:00:00',NULL,2,7,1,0,0,'Abierta','Roberto Méndez');
INSERT INTO "sesion_clase" VALUES(5,5,'2026-11-20','13:00:00',NULL,3,5,0,1,0,'Abierta','Alejandro Navarro');
INSERT INTO "sesion_clase" VALUES(6,6,'2026-11-20','13:00:00','21:54:54',2,5,1,1,0,'Cerrada','Roberto Carlos Méndez Peña');
INSERT INTO "sesion_clase" VALUES(7,1,'2026-11-22','11:36:01','11:36:01',4,1,0,0,1,'Abierta','Prof. Roberto Navarro');
CREATE TABLE "usuario" (
  "id_usuario" INTEGER PRIMARY KEY AUTOINCREMENT,
  "id_personal" INTEGER NOT NULL UNIQUE,
  "username" TEXT NOT NULL UNIQUE,
  "password_encriptada" TEXT NOT NULL,
  "rol_sistema" TEXT NOT NULL DEFAULT 'Control',
  "es_duena" INTEGER NOT NULL DEFAULT '0',
  "activo" INTEGER NOT NULL DEFAULT '1',
  "fecha_baja" TEXT,
  "motivo_baja" TEXT,
  "primer_ingreso" INTEGER NOT NULL DEFAULT '1',
  "ultimo_cambio_pass" TEXT,
  FOREIGN KEY ("id_personal") REFERENCES "personal" ("id_personal") ON DELETE CASCADE ON UPDATE CASCADE
);
INSERT INTO "usuario" VALUES(1,11,'directora','$2b$12$OLjSs41IHXUpHwAUErGdWeBHMC/EOHgOhMuyZfhbgmQZGezHTxQ/m','Directivo',1,1,NULL,NULL,0,'2026-11-21T13:14:27');
INSERT INTO "usuario" VALUES(2,7,'admin','$2b$12$cLGkip3wVRp2AIJmRL4t5OEQbUmxjanffT.DWLb4eTw9.ibRdb526','Administrador',0,1,'2026-11-20T14:53:23','Renuncia',0,'2026-11-21T21:51:19');
INSERT INTO "usuario" VALUES(3,6,'recepcion','$2b$12$wDZRdUc/AHZgCAO2g4lTBeaYMvsJOPrgQGdEW0OEYkKrREpM5C2kW','Control',0,1,'2026-11-20T14:52:32','Renuncia',1,NULL);
INSERT INTO "usuario" VALUES(4,3,'prof.navarro','$2b$12$wDZRdUc/AHZgCAO2g4lTBeaYMvsJOPrgQGdEW0OEYkKrREpM5C2kW','Docente',0,1,'2026-11-20T14:52:58','Renuncia',1,NULL);
INSERT INTO "usuario" VALUES(5,4,'prof.silva','$2b$12$wDZRdUc/AHZgCAO2g4lTBeaYMvsJOPrgQGdEW0OEYkKrREpM5C2kW','Docente',0,1,'2026-11-20T14:52:42','Renuncia',1,NULL);
INSERT INTO "usuario" VALUES(6,5,'prof.gutierrez','$2b$12$wDZRdUc/AHZgCAO2g4lTBeaYMvsJOPrgQGdEW0OEYkKrREpM5C2kW','Docente',0,1,'2026-11-20T14:53:16','Fin de Contrato',1,NULL);
INSERT INTO "usuario" VALUES(7,2,'prof.mendez','$2b$12$wDZRdUc/AHZgCAO2g4lTBeaYMvsJOPrgQGdEW0OEYkKrREpM5C2kW','Docente',0,1,'2026-11-20T14:53:08','Fin de Contrato',1,NULL);
INSERT INTO "usuario" VALUES(8,10,'vanessavmorales','$2b$12$CtbfAnmvESTc3OfYWasMReCOR/MnBQoJs7nB9KpuWzBLzD/wwzUKq','Directivo',0,0,'2026-11-20T14:54:06','Renuncia',1,NULL);
CREATE VIEW v_asistencia_total AS
  SELECT id_asistencia, id_persona, fecha, hora_entrada, hora_salida, estado, observaciones
    FROM asistencia
  UNION ALL
  SELECT id_asistencia, id_persona, fecha, hora_entrada, hora_salida, estado, observaciones
    FROM asistencia_archivo;
CREATE VIEW v_auditoria_ingresos AS
  SELECT a.fecha_hora AS "Fecha y hora",
         u.username AS "Usuario",
         (p.nombre || ' ' || p.apellido) AS "Funcionario",
         u.rol_sistema AS "Rol",
         a.equipo AS "Equipo"
    FROM auditoria_ingresos a
    JOIN usuario u ON u.id_usuario = a.id_usuario
    JOIN personal pl ON pl.id_personal = u.id_personal
    JOIN persona p ON p.id_persona = pl.id_persona
   ORDER BY a.fecha_hora DESC;
CREATE UNIQUE INDEX uq_matricula_persona_cohorte ON matricula (id_persona, id_cohorte);
CREATE UNIQUE INDEX uq_asistencia_cohorte_persona_fecha ON asistencia_curso (id_cohorte, id_persona, fecha);
CREATE UNIQUE INDEX uq_sesion_cohorte_fecha ON sesion_clase (id_cohorte, fecha);
CREATE UNIQUE INDEX uq_asistencia_persona_fecha ON asistencia (id_persona, fecha);
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('periodo',1);
INSERT INTO "sqlite_sequence" VALUES('curso',6);
INSERT INTO "sqlite_sequence" VALUES('seccion',6);
INSERT INTO "sqlite_sequence" VALUES('persona',60);
INSERT INTO "sqlite_sequence" VALUES('estudiante',58);
INSERT INTO "sqlite_sequence" VALUES('personal',11);
INSERT INTO "sqlite_sequence" VALUES('cohorte',6);
INSERT INTO "sqlite_sequence" VALUES('matricula',57);
INSERT INTO "sqlite_sequence" VALUES('sesion_clase',7);
INSERT INTO "sqlite_sequence" VALUES('usuario',9);
INSERT INTO "sqlite_sequence" VALUES('asistencia',106);
INSERT INTO "sqlite_sequence" VALUES('asistencia_curso',142);
INSERT INTO "sqlite_sequence" VALUES('auditoria_ingresos',12);
INSERT INTO "sqlite_sequence" VALUES('bitacora_asistencia',32);
INSERT INTO "sqlite_sequence" VALUES('cierre_diario',1);
INSERT INTO "sqlite_sequence" VALUES('asistencia_historico',56);
INSERT INTO "sqlite_sequence" VALUES('cierre_mensual',1);
COMMIT;

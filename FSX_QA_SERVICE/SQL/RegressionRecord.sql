SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for regression
-- ----------------------------
DROP TABLE IF EXISTS `regression`;
CREATE TABLE `RegressionRecord` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `taskId` varchar(255) NOT NULL COMMENT '任务Id',
  `status` varchar(255) DEFAULT NULL COMMENT '执行状态 1-success 2-fail 3-error',
  `type` tinyint(1) DEFAULT NULL COMMENT '项目类型 1-edp 2-rolx 3-rex',
  `CreateUser` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '创建人',
  `CreateTime` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `log_file` longblob COMMENT 'log文件',
  `excel_file` longblob COMMENT 'excel文件',
  `output` varchar(255) DEFAULT NULL COMMENT '返回信息',
  `report_filename` varchar(255) DEFAULT NULL,
  `log_filename` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `id_UNIQUE` (`id`),
  UNIQUE KEY `taskId_UNIQUE` (`taskId`)
) ENGINE=InnoDB AUTO_INCREMENT=99 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci

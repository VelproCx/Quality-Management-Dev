SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `TesecaseRecord`;
CREATE TABLE `TesecaseRecord` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '自增id',
  `source` varchar(50) DEFAULT NULL COMMENT '修改人',
  `caseName` varchar(50) NOT NULL COMMENT '用例名称',
  `updateTime` datetime COMMENT '用例文件修改标志',
  `isDelete` BOOL DEFAULT FALSE COMMENT '软删除标志',

  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用例管理';

SET FOREIGN_KEY_CHECKS = 1;
